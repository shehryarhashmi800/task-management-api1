import pytest

from app.main import app

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _operations():
    for path, item in app.openapi()["paths"].items():
        for method, operation in item.items():
            if method in HTTP_METHODS:
                yield path, method, operation


@pytest.mark.parametrize("path, method, operation", list(_operations()))
def test_every_endpoint_has_a_summary_and_description(path, method, operation):
    assert operation.get("summary"), f"{method.upper()} {path} has no summary"
    assert operation.get("description"), f"{method.upper()} {path} has no description"


@pytest.mark.parametrize(
    "path, method, operation",
    [op for op in _operations() if op[0].startswith("/api/v1/tasks")],
)
def test_task_endpoints_document_their_error_responses(path, method, operation):
    assert "401" in operation["responses"]
    assert operation["responses"]["401"]["description"]


def test_bearer_scheme_is_declared_so_swagger_authorize_accepts_a_pasted_token():
    schemes = app.openapi()["components"]["securitySchemes"]
    assert any(s.get("type") == "http" and s.get("scheme") == "bearer" for s in schemes.values())


def test_paginated_response_documents_item_schema():
    schemas = app.openapi()["components"]["schemas"]
    page = next(s for name, s in schemas.items() if name.startswith("PaginatedResponse"))
    assert {"total", "page", "page_size", "has_more", "items"} <= set(page["properties"])


def test_tags_are_described():
    tags = {t["name"]: t.get("description") for t in app.openapi()["tags"]}
    assert all(tags.values())
    assert {"auth", "tasks", "users", "health"} <= set(tags)
