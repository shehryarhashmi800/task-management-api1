"""Rate limiting for the authentication endpoints (brute-force protection)."""

from slowapi import Limiter

from app.config import settings
from app.core.client_ip import get_client_ip

limiter = Limiter(
    key_func=get_client_ip,
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=False,
)


def login_limit() -> str:
    """Current limit for POST /auth/login, e.g. ``5/minute``."""
    return settings.RATE_LIMIT_LOGIN


def register_limit() -> str:
    """Current limit for POST /auth/register."""
    return settings.RATE_LIMIT_REGISTER


def refresh_limit() -> str:
    """Current limit for POST /auth/refresh."""
    return settings.RATE_LIMIT_REFRESH
