import uuid


def _unique_username() -> str:
    return f"testuser_{uuid.uuid4().hex[:12]}"


def test_register_login_refresh_logout_flow(client) -> None:
    username = _unique_username()
    password = "correct-horse-battery-staple"

    # Register
    response = client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    tokens = response.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    # /users/me with the access token
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    assert response.json()["username"] == username

    # Duplicate registration is rejected
    response = client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USERNAME_TAKEN"

    # Login with correct credentials
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    login_tokens = response.json()

    # Login with wrong password is rejected, in the standard error shape
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "wrong"})
    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "error": {"code": "UNAUTHORIZED", "message": "Invalid username or password"},
    }

    # Refresh rotates the token
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": login_tokens["refresh_token"]})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["refresh_token"] != login_tokens["refresh_token"]

    # The old refresh token is now revoked and cannot be reused
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": login_tokens["refresh_token"]})
    assert response.status_code == 401

    # Logout revokes the current refresh token
    response = client.post("/api/v1/auth/logout", json={"refresh_token": new_tokens["refresh_token"]})
    assert response.status_code == 200
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert response.status_code == 401


def test_users_me_requires_auth(client) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_update_profile(client) -> None:
    username = _unique_username()
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        "/api/v1/users/me",
        json={"height_cm": 178.5, "weight_kg": 74.2, "goal": "gain_muscle"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profile"]["height_cm"] == 178.5
    assert body["profile"]["goal"] == "gain_muscle"
