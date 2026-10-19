"""Business logic for registration, login, token refresh and current-user lookup."""

import uuid

from sqlalchemy.orm import Session

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    TokenError,
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
    """Authentication operations, built on the user repository."""

    def __init__(self, db: Session):
        """Create the service for one database session."""
        self.db = db
        self.users = UserRepository(db)

    def register(self, data: UserCreate) -> User:
        """Create a new user, or raise AlreadyExistsError if email/username is taken."""
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
        """Check an email and password and return the user.

        A hash is checked even when the email is unknown, so the response time
        does not reveal which emails are registered.
        """
        user = self.users.get_by_email(email)
        if not user:
            verify_password(password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError()
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()
        return user

    def login(self, email: str, password: str) -> TokenResponse:
        """Log a user in and return an access token and a refresh token."""
        user = self.authenticate(email, password)
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    def refresh_access_token(self, refresh_token: str) -> str:
        """Exchange a valid refresh token for a new access token."""
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except (TokenError, ValueError):
            raise InvalidTokenError("Invalid or expired refresh token") from None

        user = self._user_from_subject(payload.get("sub"))
        if not user or not user.is_active:
            raise InvalidTokenError("User no longer exists or is inactive")

        return create_access_token(user.id)

    def get_current_user(self, access_token: str) -> User:
        """Return the user an access token belongs to, or raise InvalidTokenError."""
        try:
            payload = decode_token(access_token, expected_type="access")
        except (TokenError, ValueError):
            raise InvalidTokenError() from None

        user = self._user_from_subject(payload.get("sub"))
        if not user:
            raise InvalidTokenError("User no longer exists")
        if not user.is_active:
            raise InactiveUserError()
        return user

    def _user_from_subject(self, subject) -> User | None:
        try:
            return self.users.get(uuid.UUID(subject))
        except (ValueError, TypeError):
            return None
