import pytest

from app.config import settings

API_PATH = "/api/v1/tasks"


def test_api_responses_have_security_headers(client):
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "Permissions-Policy" in response.headers


def test_error_responses_also_have_security_headers(client):
    response = client.get(API_PATH)
    assert response.status_code == 401
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_docs_pages_skip_the_strict_csp_so_swagger_still_loads(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_auth_responses_are_not_cacheable(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert response.headers["Cache-Control"] == "no-store"


def test_hsts_only_sent_in_production(client, monkeypatch):
    assert "Strict-Transport-Security" not in client.get("/health").headers
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    header = client.get("/health").headers["Strict-Transport-Security"]
    assert "max-age=31536000" in header


def test_missing_token_gets_401_with_www_authenticate(client):
    response = client.get(API_PATH)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"] == "invalid_token"


def test_non_bearer_scheme_is_rejected(client):
    response = client.get(API_PATH, headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401


def test_oversized_body_is_rejected_with_413(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BODY_BYTES", 200)
    response = client.post(
        API_PATH, headers=auth_headers, json={"title": "x", "description": "y" * 500}
    )
    assert response.status_code == 413
    assert response.json()["error"] == "payload_too_large"


def test_cors_allows_configured_origin_and_exposes_request_id(client):
    origin = settings.cors_origins_list[0]
    response = client.options(
        API_PATH,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    simple = client.get("/health", headers={"Origin": origin})
    assert "X-Request-ID" in simple.headers["access-control-expose-headers"]


def test_cors_does_not_allow_unknown_origin(client):
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers
