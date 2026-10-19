"""Password hashing and JWT creation/verification."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DUMMY_PASSWORD_HASH = "$2b$12$kfAGJmiJOy9KlJ6NHrnBeOha/i4kijYL0f6dZrqbIncLfD0pueQEO"

TokenError = PyJWTError


def hash_password(password: str) -> str:
    """Hash a plain password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    """Create a short-lived access token for a user."""
    return _create_token(
        str(user_id),
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a long-lived refresh token for a user."""
    return _create_token(
        str(user_id),
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Verify a token's signature and expiry and return its payload.

    Raises ``TokenError`` for a bad or expired token, and ``ValueError`` if the
    token is valid but is not of the ``expected_type`` (access vs refresh).
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        leeway=10,
        options={"require": ["exp", "sub"]},
    )
    if expected_type and payload.get("type") != expected_type:
        raise ValueError(f"expected a {expected_type} token")
    return payload
