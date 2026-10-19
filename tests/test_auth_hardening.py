from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.core import security
from app.models.user import User
from app.services import auth_service

ME = "/api/v1/auth/me"


def _token(user_id, token_type="access", minutes=5, secret=None, algorithm="HS256"):
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, secret or settings.SECRET_KEY, algorithm=algorithm)


def _user_id(client, headers):
    return client.get(ME, headers=headers).json()["id"]


def test_login_for_unknown_email_still_checks_a_password_hash(client, monkeypatch):
    checked = []
    real_verify = auth_service.verify_password
    monkeypatch.setattr(
        auth_service,
        "verify_password",
        lambda plain, hashed: checked.append(hashed) or real_verify(plain, hashed),
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "Whatever1"}
    )
    assert response.status_code == 401
    assert checked == [security.DUMMY_PASSWORD_HASH]


def test_wrong_password_and_unknown_email_give_the_same_error(client, registered_user):
    wrong = client.post(
        "/api/v1/auth/login", json={"email": registered_user["email"], "password": "Nope12345"}
    )
    unknown = client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "Nope12345"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["message"] == unknown.json()["message"]


def test_expired_access_token_is_rejected(client, auth_headers):
    expired = _token(_user_id(client, auth_headers), minutes=-5)
    response = client.get(ME, headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_token_signed_with_wrong_secret_is_rejected(client, auth_headers):
    forged = _token(_user_id(client, auth_headers), secret="x" * 40)
    response = client.get(ME, headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_unsigned_alg_none_token_is_rejected(client, auth_headers):
    payload = {"sub": _user_id(client, auth_headers), "type": "access", "exp": 9999999999}
    unsigned = jwt.encode(payload, key=None, algorithm="none")
    response = client.get(ME, headers={"Authorization": f"Bearer {unsigned}"})
    assert response.status_code == 401


def test_refresh_token_cannot_be_used_as_an_access_token(client, auth_headers):
    refresh = _token(_user_id(client, auth_headers), token_type="refresh")
    response = client.get(ME, headers={"Authorization": f"Bearer {refresh}"})
    assert response.status_code == 401


def test_token_without_expiry_is_rejected(client, auth_headers):
    payload = {"sub": _user_id(client, auth_headers), "type": "access"}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    response = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_refresh_returns_a_working_access_token(client, registered_user):
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    ).json()
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    assert client.get(ME, headers=new_headers).status_code == 200


def test_token_for_a_deleted_user_is_rejected(client, db_session, auth_headers):
    user = db_session.query(User).filter_by(email="alice@example.com").one()
    db_session.delete(user)
    db_session.commit()
    assert client.get(ME, headers=auth_headers).status_code == 401


def test_inactive_user_cannot_log_in(client, db_session, registered_user):
    user = db_session.query(User).filter_by(email=registered_user["email"]).one()
    user.is_active = False
    db_session.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert response.status_code == 403
    assert response.json()["error"] == "inactive_user"


def test_existing_token_stops_working_when_user_is_deactivated(client, db_session, auth_headers):
    user = db_session.query(User).filter_by(email="alice@example.com").one()
    user.is_active = False
    db_session.commit()
    assert client.get(ME, headers=auth_headers).status_code == 403


@pytest.mark.parametrize("password", ["x" * 129, "short1", "allletters", "12345678"])
def test_unacceptable_passwords_are_rejected(client, password):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "p@example.com", "username": "puser", "password": password},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("username", ["ab", "has space", "semi;colon", "émoji", "x" * 51])
def test_unacceptable_usernames_are_rejected(client, username):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "u@example.com", "username": username, "password": "GoodPass1"},
    )
    assert response.status_code == 422


def test_passwords_are_stored_hashed(client, db_session, registered_user):
    user = db_session.query(User).filter_by(email=registered_user["email"]).one()
    assert user.hashed_password != registered_user["password"]
    assert user.hashed_password.startswith("$2")


def test_admin_user_list_requires_admin(client, db_session, auth_headers):
    assert client.get("/api/v1/users", headers=auth_headers).status_code == 403
    assert client.get("/api/v1/users").status_code == 401

    user = db_session.query(User).filter_by(email="alice@example.com").one()
    user.is_admin = True
    db_session.commit()
    response = client.get("/api/v1/users", headers=auth_headers)
    assert response.status_code == 200
    assert [u["email"] for u in response.json()] == ["alice@example.com"]
    assert "hashed_password" not in response.json()[0]


def test_admin_user_list_supports_paging(client, db_session, auth_headers, second_user_headers):
    user = db_session.query(User).filter_by(email="alice@example.com").one()
    user.is_admin = True
    db_session.commit()
    first = client.get("/api/v1/users", headers=auth_headers, params={"limit": 1})
    second = client.get("/api/v1/users", headers=auth_headers, params={"limit": 1, "skip": 1})
    assert len(first.json()) == len(second.json()) == 1
    assert first.json()[0]["id"] != second.json()[0]["id"]
