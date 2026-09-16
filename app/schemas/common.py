from typing import Any, List, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):

    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Any]
