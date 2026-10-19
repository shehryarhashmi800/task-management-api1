"""Database access for users."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Database access for users."""

    def __init__(self, db: Session):
        """Create the repository for one database session."""
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        """Return the user with this email, or None."""
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username: str) -> Optional[User]:
        """Return the user with this username, or None."""
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()
