import pytest

from app.config import settings
from app.core.rate_limit import limiter

BAD_LOGIN = {"email": "alice@example.com", "password": "WrongPass1"}


@pytest.fixture()
def rate_limit_on(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", "3/minute")
    monkeypatch.setattr(settings, "RATE_LIMIT_REGISTER", "2/minute")
    monkeypatch.setattr(settings, "RATE_LIMIT_REFRESH", "2/minute")
    limiter.reset()
    limiter.enabled = True
    yield


def test_login_is_blocked_after_too_many_attempts(client, registered_user, rate_limit_on):
    first_three = [client.post("/api/v1/auth/login", json=BAD_LOGIN).status_code for _ in range(3)]
    assert first_three == [401, 401, 401]

    blocked = client.post("/api/v1/auth/login", json=BAD_LOGIN)
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["error"] == "rate_limited"
    assert body["request_id"] == blocked.headers["X-Request-ID"]
    assert int(blocked.headers["Retry-After"]) > 0


def test_correct_password_is_also_blocked_once_limit_is_hit(client, registered_user, rate_limit_on):
    for _ in range(3):
        client.post("/api/v1/auth/login", json=BAD_LOGIN)
    good = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert good.status_code == 429


def test_register_is_rate_limited(client, rate_limit_on):
    codes = []
    for i in range(3):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": f"user{i}@example.com", "username": f"user{i}", "password": "GoodPass1"},
        )
        codes.append(response.status_code)
    assert codes == [201, 201, 429]


def test_refresh_is_rate_limited(client, rate_limit_on):
    codes = [
        client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"}).status_code
        for _ in range(3)
    ]
    assert codes == [401, 401, 429]


def test_other_endpoints_are_not_rate_limited(client, auth_headers, rate_limit_on):
    codes = {client.get("/api/v1/tasks", headers=auth_headers).status_code for _ in range(10)}
    assert codes == {200}


def test_limit_is_per_client_ip_when_proxy_headers_are_trusted(
    client, registered_user, rate_limit_on, monkeypatch
):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    for _ in range(3):
        client.post("/api/v1/auth/login", json=BAD_LOGIN, headers={"X-Forwarded-For": "1.1.1.1"})

    same_ip = client.post(
        "/api/v1/auth/login", json=BAD_LOGIN, headers={"X-Forwarded-For": "1.1.1.1"}
    )
    other_ip = client.post(
        "/api/v1/auth/login", json=BAD_LOGIN, headers={"X-Forwarded-For": "2.2.2.2"}
    )
    assert same_ip.status_code == 429
    assert other_ip.status_code == 401


def test_x_forwarded_for_is_ignored_when_proxy_is_not_trusted(
    client, registered_user, rate_limit_on, monkeypatch
):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", False)
    for i in range(3):
        client.post("/api/v1/auth/login", json=BAD_LOGIN, headers={"X-Forwarded-For": f"9.9.9.{i}"})
    spoofed = client.post(
        "/api/v1/auth/login", json=BAD_LOGIN, headers={"X-Forwarded-For": "8.8.8.8"}
    )
    assert spoofed.status_code == 429
