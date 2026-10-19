"""A generic repository with the basic create/read/update/delete operations."""

import uuid
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic create/read/update/delete operations for one model."""

    def __init__(self, model: Type[ModelType], db: Session):
        """Create the repository for one model and one database session."""
        self.model = model
        self.db = db

    def get(self, id: uuid.UUID) -> Optional[ModelType]:
        """Return the row with this id, or None."""
        return self.db.get(self.model, id)

    def create(self, obj: ModelType) -> ModelType:
        """Insert a new row and return it with database defaults filled in."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        """Save changes to an existing row and return it."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        """Delete a row."""
        self.db.delete(obj)
        self.db.commit()
