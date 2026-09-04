"""`initData` verification: signature, freshness, token rotation, and — importantly — what is
*not* rejected (app/core/telegram_webapp.py, docs/DECISIONS.md D-16, D-17, D-18).
"""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from app.core.config import get_settings
from app.services import auth_service
from tests.conftest import BOT_HEADERS, make_init_data, new_telegram_id, sign_init_data


def test_creates_a_new_account(client) -> None:
    tg_id = new_telegram_id()
    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(tg_id)})
    assert response.status_code == 200, response.text
    client.cookies.clear()

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == f"tg_{tg_id}"
    assert me.json()["first_name"] == "Smoke"


def test_the_same_init_data_may_be_presented_again(client) -> None:
    """D-17, stated as a test because it is the rule easiest to break by accident.

    A reload, a re-auth after the access token expires, and a retried request all present the
    identical `initData` string. Treating the second sighting as a replay attack would break
    ordinary use while barely inconveniencing an attacker, who can simply capture a fresh one.
    """
    tg_id = new_telegram_id()
    init_data = make_init_data(tg_id)

    first = client.post("/api/v1/auth/telegram-webapp", json={"init_data": init_data})
    second = client.post("/api/v1/auth/telegram-webapp", json={"init_data": init_data})
    third = client.post("/api/v1/auth/telegram-webapp", json={"init_data": init_data})
    client.cookies.clear()

    assert first.status_code == 200
    assert second.status_code == 200, second.text
    assert third.status_code == 200, third.text


def test_is_idempotent_per_telegram_id(client) -> None:
    tg_id = new_telegram_id()
    first = client.post("/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(tg_id)})
    second = client.post("/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(tg_id)})
    client.cookies.clear()

    me1 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {first.json()['access_token']}"})
    me2 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {second.json()['access_token']}"})
    assert me1.json()["id"] == me2.json()["id"]

    bot_login = client.post(
        "/api/v1/auth/telegram", json={"telegram_id": tg_id, "chat_id": tg_id}, headers=BOT_HEADERS
    )
    me3 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {bot_login.json()['access_token']}"})
    assert me3.json()["id"] == me1.json()["id"]


def test_rejects_a_tampered_hash(client) -> None:
    tampered = make_init_data(new_telegram_id())[:-4] + "0000"
    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": tampered})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_rejects_another_bots_signature(client) -> None:
    tg_id = new_telegram_id()
    fields = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": tg_id, "first_name": "Smoke"}, separators=(",", ":")),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    wrong_secret = hmac.new(b"WebAppData", b"someone-elses-bot-token", hashlib.sha256).digest()
    forged = urlencode({**fields, "hash": hmac.new(wrong_secret, check.encode(), hashlib.sha256).hexdigest()})

    assert client.post("/api/v1/auth/telegram-webapp", json={"init_data": forged}).status_code == 401


def test_freshness_window_is_300_seconds(client) -> None:
    """D-16 narrowed this from 24 hours. 299s must pass and 301s must not — asserting both sides
    so a future change to the constant cannot slip through by only widening one edge."""
    assert get_settings().init_data_max_age_seconds == 300

    tg_id = new_telegram_id()
    fresh = make_init_data(tg_id, auth_date=int(time.time()) - 299)
    stale = make_init_data(tg_id, auth_date=int(time.time()) - 301)

    assert client.post("/api/v1/auth/telegram-webapp", json={"init_data": fresh}).status_code == 200
    client.cookies.clear()
    expired = client.post("/api/v1/auth/telegram-webapp", json={"init_data": stale})
    assert expired.status_code == 401
    assert "expired" in expired.json()["error"]["message"]


def test_previous_bot_token_is_accepted_during_rotation(client, monkeypatch) -> None:
    """D-18: rotating the bot token must not sign every open Mini App out at once."""
    from app.core import telegram_webapp as tw

    rotated_in = "rotated-in-bot-token"
    old_token = get_settings().telegram_bot_token

    class _RotatingSettings:
        init_data_max_age_seconds = 300
        telegram_bot_token = rotated_in
        telegram_bot_token_previous = old_token
        telegram_bot_tokens = [rotated_in, old_token]

    monkeypatch.setattr(tw, "settings", _RotatingSettings())
    monkeypatch.setattr(auth_service, "settings", _RotatingSettings())

    tg_id = new_telegram_id()
    signed_with_old = make_init_data(tg_id, bot_token=old_token)
    signed_with_new = make_init_data(tg_id, bot_token=rotated_in)

    assert client.post("/api/v1/auth/telegram-webapp", json={"init_data": signed_with_old}).status_code == 200
    client.cookies.clear()
    assert client.post("/api/v1/auth/telegram-webapp", json={"init_data": signed_with_new}).status_code == 200
    client.cookies.clear()


def test_language_comes_from_the_telegram_client(client) -> None:
    """D-53: uz* -> uz, ru* -> ru, anything else -> en."""
    for language_code, expected in [("ru-RU", "ru"), ("uz", "uz"), ("de-DE", "en")]:
        tg_id = new_telegram_id()
        init_data = make_init_data(tg_id, language_code=language_code)
        token = client.post("/api/v1/auth/telegram-webapp", json={"init_data": init_data}).json()["access_token"]
        client.cookies.clear()
        me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me.json()["language"] == expected, language_code


def test_rejects_missing_init_data(client) -> None:
    assert client.post("/api/v1/auth/telegram-webapp", json={"init_data": ""}).status_code in (401, 422)


def test_returns_503_when_no_bot_token_is_configured(client, monkeypatch) -> None:
    class _NoTelegramSettings:
        telegram_bot_tokens: list[str] = []

    monkeypatch.setattr(auth_service, "settings", _NoTelegramSettings())
    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(new_telegram_id())})
    assert response.status_code == 503


def test_unsigned_payload_is_never_counted_by_the_abuse_guard(client, monkeypatch) -> None:
    """The repeat counter runs only after the signature checks out — otherwise anyone could fill
    it with garbage and there would be no way to tell abuse from noise."""
    seen: list[str] = []

    async def _spy(init_data: str) -> int:
        seen.append(init_data)
        return 1

    monkeypatch.setattr(auth_service, "record_and_check", _spy)
    client.post("/api/v1/auth/telegram-webapp", json={"init_data": "garbage"})
    assert seen == []

    valid = make_init_data(new_telegram_id())
    client.post("/api/v1/auth/telegram-webapp", json={"init_data": valid})
    client.cookies.clear()
    assert seen == [valid]
