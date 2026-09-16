def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "username": "newuser",
            "password": "GoodPass1",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["username"] == "newuser"
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_duplicate_email_fails(client, registered_user):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": registered_user["email"],
            "username": "someoneelse",
            "password": "GoodPass1",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"] == "already_exists"


def test_register_duplicate_username_fails(client, registered_user):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "different@example.com",
            "username": registered_user["username"],
            "password": "GoodPass1",
        },
    )
    assert response.status_code == 409


def test_register_weak_password_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "username": "weakuser", "password": "short"},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_register_invalid_email_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "username": "someuser", "password": "GoodPass1"},
    )
    assert response.status_code == 422


def test_login_success(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password_fails(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": "WrongPass1"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "invalid_credentials"


def test_login_nonexistent_user_fails(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "WhoKnows1"},
    )
    assert response.status_code == 401


def test_get_current_user(client, auth_headers, registered_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == registered_user["email"]


def test_get_current_user_no_token_fails(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token_fails(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_refresh_token_success(client, registered_user):
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_refresh_with_access_token_fails(client, auth_headers):
    access_token = auth_headers["Authorization"].split(" ")[1]
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_refresh_with_garbage_token_fails(client):
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
    assert response.status_code == 401
