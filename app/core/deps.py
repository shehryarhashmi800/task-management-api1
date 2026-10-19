"""FastAPI dependencies that identify the caller."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import ForbiddenError, InvalidTokenError
from app.models.user import User
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Paste the `access_token` returned by `POST /api/v1/auth/login`.",
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the logged-in user, or raise a 401 if the token is missing or bad."""
    if credentials is None:
        raise InvalidTokenError("Not authenticated")
    return AuthService(db).get_current_user(credentials.credentials)


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the logged-in user only if they are an admin, otherwise raise a 403."""
    if not current_user.is_admin:
        raise ForbiddenError("Admin privileges required")
    return current_user
