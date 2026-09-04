"""The bot's door: POST /auth/telegram.

Account *linking* used to live here, as a password-verified way to attach a Telegram id to a web
account. With Telegram as the only identity (D-10) there is nothing to link — the Telegram id is
the account — so those tests are gone rather than rewritten.
"""

from tests.conftest import BOT_HEADERS, make_init_data, new_telegram_id


def test_bot_auth_creates_new_account(client) -> None:
    tg_id = new_telegram_id()
    response = client.post(
        "/api/v1/auth/telegram",
        json={"telegram_id": tg_id, "chat_id": tg_id, "telegram_username": "smoketest", "first_name": "Smoke"},
        headers=BOT_HEADERS,
    )
    assert response.status_code == 200, response.text
    tokens = response.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == f"tg_{tg_id}"
    assert me.json()["first_name"] == "Smoke"


def test_bot_auth_is_idempotent_for_same_telegram_id(client) -> None:
    tg_id = new_telegram_id()
    payload = {"telegram_id": tg_id, "chat_id": tg_id}
    first = client.post("/api/v1/auth/telegram", json=payload, headers=BOT_HEADERS)
    second = client.post("/api/v1/auth/telegram", json=payload, headers=BOT_HEADERS)
    assert first.status_code == 200 and second.status_code == 200

    me1 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {first.json()['access_token']}"})
    me2 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {second.json()['access_token']}"})
    # Same telegram_id -> same account, not a fresh tg_<id>_1 on every call.
    assert me1.json()["id"] == me2.json()["id"]


def test_bot_and_mini_app_reach_the_same_account(client) -> None:
    """One person, one account, regardless of which surface they opened first — the property
    that makes account linking unnecessary."""
    tg_id = new_telegram_id()

    via_bot = client.post(
        "/api/v1/auth/telegram", json={"telegram_id": tg_id, "chat_id": tg_id}, headers=BOT_HEADERS
    )
    via_mini_app = client.post("/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(tg_id)})
    client.cookies.clear()

    me_bot = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {via_bot.json()['access_token']}"})
    me_app = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {via_mini_app.json()['access_token']}"}
    )
    assert me_bot.json()["id"] == me_app.json()["id"]


def test_bot_refresh_rotates_and_detects_reuse(client) -> None:
    tg_id = new_telegram_id()
    tokens = client.post(
        "/api/v1/auth/telegram", json={"telegram_id": tg_id, "chat_id": tg_id}, headers=BOT_HEADERS
    ).json()

    rotated = client.post(
        "/api/v1/auth/bot/refresh", json={"refresh_token": tokens["refresh_token"]}, headers=BOT_HEADERS
    )
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != tokens["refresh_token"]

    # The bot's sessions get the same family protection as the browser's (D-14).
    replay = client.post(
        "/api/v1/auth/bot/refresh", json={"refresh_token": tokens["refresh_token"]}, headers=BOT_HEADERS
    )
    assert replay.status_code == 401


def test_bot_refresh_requires_the_shared_secret(client) -> None:
    tg_id = new_telegram_id()
    tokens = client.post(
        "/api/v1/auth/telegram", json={"telegram_id": tg_id, "chat_id": tg_id}, headers=BOT_HEADERS
    ).json()
    response = client.post("/api/v1/auth/bot/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 401
