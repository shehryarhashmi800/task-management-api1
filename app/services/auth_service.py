import uuid

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.exceptions import (
    AlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, data: UserCreate) -> User:
        if self.users.get_by_email(data.email):
            raise AlreadyExistsError("A user with this email already exists")
        if self.users.get_by_username(data.username):
            raise AlreadyExistsError("This username is already taken")

        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
        )
        return self.users.create(user)

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()
        return user

    def login(self, email: str, password: str) -> TokenResponse:
        user = self.authenticate(email, password)
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    def refresh_access_token(self, refresh_token: str) -> str:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except (JWTError, ValueError):
            raise InvalidTokenError("Invalid or expired refresh token")

        user_id = payload.get("sub")
        try:
            user = self.users.get(uuid.UUID(user_id))
        except (ValueError, TypeError):
            user = None

        if not user or not user.is_active:
            raise InvalidTokenError("User no longer exists or is inactive")

        return create_access_token(user.id)

    def get_current_user(self, access_token: str) -> User:
        try:
            payload = decode_token(access_token, expected_type="access")
        except (JWTError, ValueError):
            raise InvalidTokenError()

        user_id = payload.get("sub")
        try:
            user = self.users.get(uuid.UUID(user_id))
        except (ValueError, TypeError):
            user = None

        if not user:
            raise InvalidTokenError("User no longer exists")
        if not user.is_active:
            raise InactiveUserError()
        return user
