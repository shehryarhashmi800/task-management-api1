"""Deliberate-failure endpoint for proving Sentry works. Off unless enabled."""

from fastapi import APIRouter, Depends

from app.config import settings
from app.exceptions import NotFoundError

router = APIRouter(prefix="/api/v1/debug", tags=["debug"], include_in_schema=False)


def require_debug_enabled() -> None:
    """Pretend these routes do not exist unless ENABLE_DEBUG_ROUTES is true."""
    if not settings.ENABLE_DEBUG_ROUTES:
        raise NotFoundError("Not Found")


@router.get("/sentry-test", dependencies=[Depends(require_debug_enabled)])
def sentry_test():
    """Raise an error on purpose so it shows up in Sentry."""
    raise ZeroDivisionError("Deliberate Sentry test error")
