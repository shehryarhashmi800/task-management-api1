import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger("task_api")


class AppException(Exception):

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "internal_error"

    def __init__(self, message: str = "An unexpected error occurred"):
        self.message = message
        super().__init__(message)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)


class AlreadyExistsError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "already_exists"

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message)


class InvalidCredentialsError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "invalid_credentials"

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message)


class InvalidTokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "invalid_token"

    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(message)


class InactiveUserError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "inactive_user"

    def __init__(self, message: str = "This account is inactive"):
        super().__init__(message)


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"

    def __init__(self, message: str = "You do not have access to this resource"):
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.error_code, message=exc.message
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        details = [
            ErrorDetail(
                field=".".join(str(p) for p in err["loc"] if p != "body"),
                message=err["msg"],
            )
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="validation_error",
                message="One or more fields failed validation",
                details=details,
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="http_error", message=str(exc.detail)
            ).model_dump(),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning("Database integrity error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(
                error="conflict", message="This operation violates a data constraint"
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="internal_error", message="An unexpected error occurred"
            ).model_dump(),
        )
