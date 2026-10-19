import sentry_sdk

from app.config import settings
from app.core import observability

DEBUG_URL = "/api/v1/debug/sentry-test"


def test_debug_route_looks_nonexistent_when_disabled(client):
    response = client.get(DEBUG_URL)
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_debug_route_is_hidden_from_the_docs(client):
    assert DEBUG_URL not in client.get("/openapi.json").json()["paths"]


def test_unhandled_error_returns_a_safe_500_with_request_id(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DEBUG_ROUTES", True)
    response = client.get(DEBUG_URL)
    body = response.json()
    assert response.status_code == 500
    assert body["error"] == "internal_error"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert "ZeroDivisionError" not in response.text
    assert "Traceback" not in response.text
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_unhandled_error_is_sent_to_sentry_with_the_request_id(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DEBUG_ROUTES", True)
    events = []

    def capture(event, hint):
        events.append(event)
        return None

    sentry_sdk.init(dsn="https://public@example.invalid/1", before_send=capture)
    try:
        response = client.get(DEBUG_URL)
    finally:
        sentry_sdk.init()

    assert response.status_code == 500
    exception_types = [e["exception"]["values"][0]["type"] for e in events if "exception" in e]
    assert "ZeroDivisionError" in exception_types
    assert any(
        e.get("tags", {}).get("request_id") == response.headers["X-Request-ID"] for e in events
    )


def test_sentry_stays_off_without_a_dsn(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", None)
    assert observability.init_sentry() is False


def test_sentry_turns_on_when_a_dsn_is_set(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://public@example.invalid/1")
    try:
        assert observability.init_sentry() is True
        assert sentry_sdk.get_client().options["send_default_pii"] is False
        assert sentry_sdk.get_client().options["max_request_body_size"] == "never"
    finally:
        sentry_sdk.init()
