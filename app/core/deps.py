from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    return AuthService(db).get_current_user(token)


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    from app.exceptions import ForbiddenError

    if not current_user.is_admin:
        raise ForbiddenError("Admin privileges required")
    return current_user
