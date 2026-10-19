"""Schemas shared by several endpoints: errors and paginated lists."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """One problem with one field of a request."""

    field: str | None = Field(None, description="Name of the field that failed.")
    message: str = Field(..., description="What is wrong with the field.")


class ErrorResponse(BaseModel):
    """The single error shape returned by every failing endpoint."""

    error: str = Field(..., description="Short machine-readable code, e.g. not_found.")
    message: str = Field(..., description="Human-readable explanation.")
    details: list[ErrorDetail] | None = Field(
        None, description="Per-field problems (validation errors only)."
    )
    request_id: str | None = Field(
        None,
        description="ID of this request. Quote it when reporting a problem.",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """A page of results plus the information needed to fetch the next page."""

    total: int = Field(..., description="Total matching items across all pages.")
    page: int = Field(..., description="Current page number, starting at 1.")
    page_size: int = Field(..., description="Maximum items per page.")
    has_more: bool = Field(..., description="True if another page exists after this.")
    items: list[T]


_ERROR_DESCRIPTIONS = {
    400: "The request could not be understood.",
    401: "Missing, invalid or expired token.",
    403: "You are not allowed to do this.",
    404: "The requested resource does not exist (or is not yours).",
    409: "The request conflicts with existing data.",
    413: "The request body is too large.",
    422: "The request body or parameters failed validation.",
    429: "Too many requests. Wait for the Retry-After period and try again.",
}


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Build the OpenAPI ``responses`` entries for the given error status codes."""
    return {
        code: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[code]} for code in codes
    }
