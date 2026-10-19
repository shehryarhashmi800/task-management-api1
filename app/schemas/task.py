"""Request and response bodies for tasks, with input sanitization."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.sanitize import sanitize_text
from app.models.task import TaskPriority, TaskStatus

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 5000
_MAX_RAW_LENGTH = 20000


def _clean_title(value: str) -> str:
    if len(value) > _MAX_RAW_LENGTH:
        raise ValueError(f"title must be {MAX_TITLE_LENGTH} characters or fewer")
    cleaned = sanitize_text(value, multiline=False)
    if not cleaned:
        raise ValueError("title must not be empty")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValueError(f"title must be {MAX_TITLE_LENGTH} characters or fewer")
    return cleaned


def _clean_description(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) > _MAX_RAW_LENGTH:
        raise ValueError(f"description must be {MAX_DESCRIPTION_LENGTH} characters or fewer")
    cleaned = sanitize_text(value, multiline=True)
    if len(cleaned) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(f"description must be {MAX_DESCRIPTION_LENGTH} characters or fewer")
    return cleaned or None


class TaskBase(BaseModel):
    """Fields shared by task requests and responses."""

    title: str = Field(..., examples=["Buy milk"])
    description: str | None = Field(None, examples=["Two litres, semi-skimmed"])
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None


class TaskCreate(TaskBase):
    """Body of the create-task request. Text fields are sanitized on the way in."""

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        """Strip HTML and control characters; reject empty or over-long titles."""
        return _clean_title(v)

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str | None) -> str | None:
        """Strip HTML and control characters; turn an empty description into null."""
        return _clean_description(v)


class TaskUpdate(BaseModel):
    """Body of an update request. Only the fields you send are changed."""

    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str | None) -> str | None:
        """Same title rules as when creating a task."""
        if v is None:
            return v
        return _clean_title(v)

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str | None) -> str | None:
        """Same description rules as when creating a task."""
        return _clean_description(v)


class TaskResponse(TaskBase):
    """A task as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
