import json
import logging
import uuid

from app.core.logging_config import JsonFormatter, request_id_ctx


def test_every_response_has_a_uuid_request_id(client):
    response = client.get("/health")
    request_id = response.headers["X-Request-ID"]
    assert str(uuid.UUID(request_id)) == request_id


def test_each_request_gets_a_different_id(client):
    ids = {client.get("/health").headers["X-Request-ID"] for _ in range(5)}
    assert len(ids) == 5


def test_error_body_contains_the_same_request_id_as_the_header(client):
    response = client.get("/api/v1/tasks")
    assert response.status_code == 401
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_validation_error_includes_request_id_and_details(client):
    response = client.post("/api/v1/auth/register", json={"email": "nope"})
    body = response.json()
    assert response.status_code == 422
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["details"]


def test_unknown_route_uses_the_standard_error_shape(client):
    response = client.get("/does-not-exist")
    body = response.json()
    assert response.status_code == 404
    assert body["error"] == "not_found"
    assert set(body) <= {"error", "message", "details", "request_id"}


def test_wrong_method_uses_the_standard_error_shape(client):
    response = client.delete("/health")
    assert response.status_code == 405
    assert response.json()["error"] == "method_not_allowed"


def test_request_is_logged_with_structured_fields(client, caplog):
    caplog.set_level(logging.INFO, logger="task_api")
    response = client.get("/api/v1/auth/me")
    records = [r for r in caplog.records if r.name == "task_api" and hasattr(r, "status_code")]
    assert records, "no request log line was written"
    record = records[-1]
    assert record.request_id == response.headers["X-Request-ID"]
    assert record.status_code == 401
    assert record.method == "GET"
    assert record.path == "/api/v1/auth/me"
    assert record.duration_ms >= 0
    assert record.levelno == logging.WARNING


def test_newlines_in_the_url_cannot_forge_log_lines(client, caplog):
    caplog.set_level(logging.INFO, logger="task_api")
    client.get("/fake%0AINFO%20forged%20line")
    paths = [r.path for r in caplog.records if hasattr(r, "path")]
    assert paths and all("\n" not in p for p in paths)


def test_json_formatter_outputs_valid_json_with_request_id():
    token = request_id_ctx.set("abc-123")
    try:
        record = logging.LogRecord(
            "task_api", logging.INFO, __file__, 1, "hello %s", ("world",), None
        )
        record.request_id = "abc-123"
        record.custom_field = 42
        parsed = json.loads(JsonFormatter().format(record))
    finally:
        request_id_ctx.reset(token)
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "INFO"
    assert parsed["request_id"] == "abc-123"
    assert parsed["custom_field"] == 42
    assert parsed["timestamp"].endswith("+00:00")


def test_json_formatter_includes_tracebacks():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord(
            "task_api", logging.ERROR, __file__, 1, "failed", (), sys.exc_info()
        )
    parsed = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in parsed["exception"]
