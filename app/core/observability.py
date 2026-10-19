"""Sentry error tracking. It only turns on when SENTRY_DSN is set."""

import logging

import sentry_sdk

from app.config import settings

logger = logging.getLogger("task_api")


def init_sentry() -> bool:
    """Start Sentry if a DSN is configured. Returns True if it was started."""
    if not settings.SENTRY_DSN:
        logger.info("Sentry disabled (no SENTRY_DSN set)")
        return False

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.SENTRY_RELEASE,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
        max_request_body_size="never",
    )
    logger.info("Sentry enabled", extra={"sentry_environment": settings.ENVIRONMENT})
    return True
