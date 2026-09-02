import uuid


def _telegram_id() -> int:
    # Telegram user ids are real int64s; a random one keeps tests independent.
    return uuid.uuid4().int % (10**9)


def test_telegram_auth_creates_new_account(client) -> None:
    tg_id = _telegram_id()
    response = client.post(
        "/api/v1/auth/telegram",
        json={"telegram_id": tg_id, "chat_id": tg_id, "telegram_username": "smoketest", "first_name": "Smoke"},
    )
    assert response.status_code == 200, response.text
    tokens = response.json()
    assert tokens["access_token"]

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == f"tg_{tg_id}"
    assert me.json()["first_name"] == "Smoke"


def test_telegram_auth_is_idempotent_for_same_telegram_id(client) -> None:
    tg_id = _telegram_id()
    first = client.post("/api/v1/auth/telegram", json={"telegram_id": tg_id, "chat_id": tg_id})
    second = client.post("/api/v1/auth/telegram", json={"telegram_id": tg_id, "chat_id": tg_id})
    assert first.status_code == 200 and second.status_code == 200

    me1 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {first.json()['access_token']}"})
    me2 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {second.json()['access_token']}"})
    # Same telegram_id -> same underlying user account both times, not a fresh tg_<id>_1 each call.
    assert me1.json()["id"] == me2.json()["id"]


def test_link_telegram_to_existing_web_account(client) -> None:
    username = f"weblink_{uuid.uuid4().hex[:10]}"
    register = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    web_token = register.json()["access_token"]

    tg_id = _telegram_id()
    response = client.post(
        "/api/v1/users/me/link-telegram",
        json={"telegram_id": tg_id, "chat_id": tg_id, "telegram_username": "webuser_on_tg"},
        headers={"Authorization": f"Bearer {web_token}"},
    )
    assert response.status_code == 200, response.text

    # After linking, POST /auth/telegram for that telegram_id logs into the *web* account, not a
    # newly auto-provisioned tg_<id> one.
    telegram_login = client.post("/api/v1/auth/telegram", json={"telegram_id": tg_id, "chat_id": tg_id})
    me = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {telegram_login.json()['access_token']}"}
    )
    assert me.json()["username"] == username


def test_cannot_link_telegram_id_already_linked_to_another_user(client) -> None:
    tg_id = _telegram_id()
    client.post("/api/v1/auth/telegram", json={"telegram_id": tg_id, "chat_id": tg_id})

    username = f"weblink2_{uuid.uuid4().hex[:10]}"
    register = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    web_token = register.json()["access_token"]

    response = client.post(
        "/api/v1/users/me/link-telegram",
        json={"telegram_id": tg_id, "chat_id": tg_id},
        headers={"Authorization": f"Bearer {web_token}"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TELEGRAM_ALREADY_LINKED"


def test_link_telegram_requires_auth(client) -> None:
    response = client.post("/api/v1/users/me/link-telegram", json={"telegram_id": 1, "chat_id": 1})
    assert response.status_code == 401
