"""Custom exceptions and the handlers that turn every error into one JSON shape."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging_config import get_request_id
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger("task_api")

_HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
}


class AppException(Exception):
    """Base class for errors the API raises on purpose."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "internal_error"

    def __init__(self, message: str = "An unexpected error occurred"):
        """Store the message that will be shown to the client."""
        self.message = message
        super().__init__(message)


class NotFoundError(AppException):
    """The requested resource does not exist (or belongs to someone else)."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"

    def __init__(self, message: str = "Resource not found"):
        """Create a 404 error."""
        super().__init__(message)


class AlreadyExistsError(AppException):
    """A unique value (email, username) is already taken."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "already_exists"

    def __init__(self, message: str = "Resource already exists"):
        """Create a 409 error."""
        super().__init__(message)


class InvalidCredentialsError(AppException):
    """Wrong email or password."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "invalid_credentials"

    def __init__(self, message: str = "Invalid email or password"):
        """Create a 401 error for a failed login."""
        super().__init__(message)


class InvalidTokenError(AppException):
    """The access or refresh token is missing, malformed or expired."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "invalid_token"

    def __init__(self, message: str = "Could not validate credentials"):
        """Create a 401 error for a bad token."""
        super().__init__(message)


class InactiveUserError(AppException):
    """The account exists but has been deactivated."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "inactive_user"

    def __init__(self, message: str = "This account is inactive"):
        """Create a 403 error for a deactivated account."""
        super().__init__(message)


class ForbiddenError(AppException):
    """The user is logged in but not allowed to do this."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"

    def __init__(self, message: str = "You do not have access to this resource"):
        """Create a 403 error."""
        super().__init__(message)


def error_response(
    status_code: int,
    error: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the standard error response, including the current request ID."""
    request_id = get_request_id()
    body = ErrorResponse(
        error=error, message=message, details=details, request_id=request_id
    ).model_dump(exclude_none=True)
    response_headers = dict(headers or {})
    if request_id:
        response_headers["X-Request-ID"] = request_id
    return JSONResponse(status_code=status_code, content=body, headers=response_headers)


def server_error_response() -> JSONResponse:
    """The generic 500 response. It never reveals internal details."""
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error",
        "An unexpected error occurred",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all error handlers to the app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        headers = {}
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            headers["WWW-Authenticate"] = "Bearer"
        return error_response(exc.status_code, exc.error_code, exc.message, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = [
            ErrorDetail(
                field=".".join(str(p) for p in err["loc"] if p != "body"),
                message=err["msg"],
            )
            for err in exc.errors()
        ]
        return error_response(
            422,
            "validation_error",
            "One or more fields failed validation",
            details=details,
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        try:
            retry_after = int(exc.limit.limit.get_expiry())
        except Exception:
            retry_after = 60
        return error_response(
            429,
            "rate_limited",
            "Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": str(retry_after)},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = _HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        headers = dict(getattr(exc, "headers", None) or {})
        return error_response(exc.status_code, code, str(exc.detail), headers=headers)

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning("Database integrity error", exc_info=exc)
        return error_response(
            status.HTTP_409_CONFLICT,
            "conflict",
            "This operation violates a data constraint",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return server_error_response()
