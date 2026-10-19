"""Middleware: request IDs, structured request logs, security headers, body limit."""

import logging
import time
import uuid

import sentry_sdk
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.core.client_ip import get_client_ip
from app.core.logging_config import request_id_ctx
from app.exceptions import error_response, server_error_response

logger = logging.getLogger("task_api")

_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")

_BASE_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Resource-Policy": "same-site",
}
_API_CSP = "default-src 'none'; frame-ancestors 'none'"
_HSTS = "max-age=31536000; includeSubDomains"


def apply_security_headers(response: Response, path: str) -> None:
    """Add the standard security headers to a response.

    The strict Content-Security-Policy is skipped for the Swagger/ReDoc pages
    because they load scripts and styles from a CDN and would break.
    """
    for name, value in _BASE_SECURITY_HEADERS.items():
        response.headers[name] = value
    if not path.startswith(_DOCS_PATHS):
        response.headers["Content-Security-Policy"] = _API_CSP
    if path.startswith(f"{settings.API_V1_PREFIX}/auth"):
        response.headers["Cache-Control"] = "no-store"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = _HSTS


def _printable(text: str) -> str:
    """Escape line breaks so a crafted URL cannot forge extra log lines."""
    return text.replace("\n", "\\n").replace("\r", "\\r")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Give every request a UUID, log it, and add the security headers."""

    async def dispatch(self, request: Request, call_next):
        """Handle one request from start to finish."""
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)
        request.state.request_id = request_id
        sentry_sdk.set_tag("request_id", request_id)

        path = request.url.path
        client_ip = get_client_ip(request)
        started = time.perf_counter()

        declared_length = request.headers.get("content-length", "")
        if declared_length.isdigit() and int(declared_length) > settings.MAX_REQUEST_BODY_BYTES:
            response = error_response(413, "payload_too_large", "The request body is too large")
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                logger.exception("Unhandled exception on %s %s", request.method, _printable(path))
                sentry_sdk.capture_exception(exc)
                response = server_error_response()

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        apply_security_headers(response, path)

        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING
        elif path == "/health":
            level = logging.DEBUG
        else:
            level = logging.INFO
        logger.log(
            level,
            "%s %s -> %s",
            request.method,
            _printable(path),
            response.status_code,
            extra={
                "method": request.method,
                "path": _printable(path),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            },
        )
        return response
