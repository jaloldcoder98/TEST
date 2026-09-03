"""Tests for POST /auth/telegram-webapp and its underlying init-data verification
(app/core/telegram_webapp.py). conftest.py sets TELEGRAM_BOT_TOKEN=test-telegram-bot-token before
the app is imported, so `_sign` below reproduces exactly what a real Telegram client would send
for that bot token.
"""

import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import urlencode

from app.services import auth_service

BOT_TOKEN = "test-telegram-bot-token"


def _telegram_id() -> int:
    return uuid.uuid4().int % (10**9)


def _sign(fields: dict) -> str:
    """Builds a real Telegram Web App `initData` string for `fields`, signed the same way
    Telegram itself does — see https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app.
    """
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": computed_hash})


def _init_data(telegram_id: int, *, username: str | None = "smoketest", first_name: str = "Smoke", auth_date: int | None = None) -> str:
    user = {"id": telegram_id, "first_name": first_name}
    if username:
        user["username"] = username
    return _sign({"user": json.dumps(user), "auth_date": str(auth_date if auth_date is not None else int(time.time()))})


def test_telegram_webapp_auth_creates_new_account(client) -> None:
    tg_id = _telegram_id()
    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": _init_data(tg_id)})
    assert response.status_code == 200, response.text
    tokens = response.json()

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == f"tg_{tg_id}"
    assert me.json()["first_name"] == "Smoke"


def test_telegram_webapp_auth_is_idempotent_and_matches_bot_login(client) -> None:
    tg_id = _telegram_id()
    first = client.post("/api/v1/auth/telegram-webapp", json={"init_data": _init_data(tg_id)})
    second = client.post("/api/v1/auth/telegram-webapp", json={"init_data": _init_data(tg_id)})
    assert first.status_code == 200 and second.status_code == 200

    me1 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {first.json()['access_token']}"})
    me2 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {second.json()['access_token']}"})
    assert me1.json()["id"] == me2.json()["id"]

    # The bot itself hitting /auth/telegram for the *same* telegram_id logs into the same account
    # — one person, one account, regardless of which surface they used first.
    bot_login = client.post("/api/v1/auth/telegram", json={"telegram_id": tg_id, "chat_id": tg_id})
    me3 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {bot_login.json()['access_token']}"})
    assert me3.json()["id"] == me1.json()["id"]


def test_telegram_webapp_auth_rejects_tampered_hash(client) -> None:
    tg_id = _telegram_id()
    valid = _init_data(tg_id)
    tampered = valid[:-4] + "0000"  # corrupt the trailing hex of the signature
    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": tampered})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_telegram_webapp_auth_rejects_wrong_bot_signature(client) -> None:
    tg_id = _telegram_id()
    user = {"id": tg_id, "first_name": "Smoke"}
    fields = {"user": json.dumps(user), "auth_date": str(int(time.time()))}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    wrong_secret = hmac.new(b"WebAppData", b"someone-elses-bot-token", hashlib.sha256).digest()
    wrong_hash = hmac.new(wrong_secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    forged = urlencode({**fields, "hash": wrong_hash})

    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": forged})
    assert response.status_code == 401


def test_telegram_webapp_auth_rejects_stale_auth_date(client) -> None:
    tg_id = _telegram_id()
    stale = _init_data(tg_id, auth_date=int(time.time()) - 2 * 24 * 60 * 60)
    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": stale})
    assert response.status_code == 401


def test_telegram_webapp_auth_rejects_missing_init_data(client) -> None:
    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": ""})
    assert response.status_code in (401, 422)


def test_telegram_webapp_auth_returns_503_when_bot_token_unset(client, monkeypatch) -> None:
    class _NoTelegramSettings:
        telegram_bot_token = None

    monkeypatch.setattr(auth_service, "get_settings", lambda: _NoTelegramSettings())
    tg_id = _telegram_id()
    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": _init_data(tg_id)})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TELEGRAM_NOT_CONFIGURED"
