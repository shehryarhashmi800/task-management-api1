"""Request and response bodies for users."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Fields shared by user requests and responses."""

    email: EmailStr = Field(..., max_length=255)
    username: str

    @field_validator("username")
    @classmethod
    def username_length(cls, v: str) -> str:
        """Allow 3-50 letters, numbers or underscores."""
        if not (3 <= len(v) <= 50):
            raise ValueError("username must be between 3 and 50 characters")
        if not (v.replace("_", "").isascii() and v.replace("_", "").isalnum()):
            raise ValueError("username may only contain letters, numbers, and underscores")
        return v


class UserCreate(UserBase):
    """Body of the register request."""

    password: str = Field(..., max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Require at least 8 characters including a letter and a digit."""
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters long")
        if not any(c.isdigit() for c in v):
            raise ValueError("password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("password must contain at least one letter")
        return v


class UserResponse(UserBase):
    """A user as returned by the API. Never includes the password."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
