"""Session lifecycle: the Mini App's cookie session, rotation, reuse detection and CSRF.

Cookie-carrying flows use their own `TestClient` rather than the shared session-scoped one, so a
test's cookie jar is its own and rotations here cannot leak into unrelated tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.cookies import cookie_name
from app.main import app
from tests.conftest import BOT_HEADERS, make_init_data, new_telegram_id


@pytest.fixture
def web():
    """A browser-like client: keeps cookies, like the Mini App's WebView does."""
    with TestClient(app) as c:
        yield c


def _sign_in(web_client, telegram_id: int | None = None):
    telegram_id = telegram_id or new_telegram_id()
    response = web_client.post(
        "/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(telegram_id)}
    )
    assert response.status_code == 200, response.text
    return response.json(), telegram_id


def test_mini_app_sign_in_returns_access_and_csrf_but_never_the_refresh_token(web) -> None:
    body, telegram_id = _sign_in(web)

    assert body["access_token"] and body["csrf_token"]
    # D-12/D-13: the refresh token must never be readable by the page.
    assert "refresh_token" not in body
    assert cookie_name() in web.cookies

    me = web.get("/api/v1/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == f"tg_{telegram_id}"
    assert me.json()["role"] == "user"


def test_refresh_rotates_the_session(web) -> None:
    body, _ = _sign_in(web)
    first_cookie = web.cookies.get(cookie_name())

    response = web.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": body["csrf_token"]})
    assert response.status_code == 200, response.text
    rotated = response.json()

    assert rotated["access_token"] != body["access_token"]
    assert rotated["csrf_token"] != body["csrf_token"]
    assert web.cookies.get(cookie_name()) != first_cookie


def test_reusing_a_rotated_token_kills_the_whole_family(web) -> None:
    """The heart of D-14. A rotated-away token reappearing means a copy is loose; revoking only
    that token would leave whoever holds its sibling still signed in."""
    body, _ = _sign_in(web)
    stale_cookie = web.cookies.get(cookie_name())
    stale_csrf = body["csrf_token"]

    rotated = web.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": stale_csrf}).json()
    live_cookie = web.cookies.get(cookie_name())

    # Replay the token that was already rotated away.
    web.cookies.set(cookie_name(), stale_cookie)
    replay = web.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": stale_csrf})
    assert replay.status_code == 401
    assert "revoked" in replay.json()["error"]["message"]

    # The legitimate, current token is now dead too — that is the point of family revocation.
    web.cookies.set(cookie_name(), live_cookie)
    after = web.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": rotated["csrf_token"]})
    assert after.status_code == 401


def test_refresh_requires_the_csrf_header(web) -> None:
    _sign_in(web)
    assert web.post("/api/v1/auth/refresh").status_code == 403
    assert web.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "wrong"}).status_code == 403


def test_refresh_rejects_a_foreign_origin(web) -> None:
    body, _ = _sign_in(web)
    response = web.post(
        "/api/v1/auth/refresh",
        headers={"X-CSRF-Token": body["csrf_token"], "Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_FAILED"


def test_refresh_without_a_cookie_is_401_not_an_error_page(web) -> None:
    """The ordinary state on Telegram Web/Safari, where the cookie may never have been stored.
    The client's correct response is silent re-auth (D-15), so this must be a plain 401."""
    response = web.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "anything"})
    assert response.status_code == 401


def test_logout_revokes_the_session_and_clears_the_cookie(web) -> None:
    body, _ = _sign_in(web)
    cookie = web.cookies.get(cookie_name())

    response = web.post("/api/v1/auth/logout", headers={"X-CSRF-Token": body["csrf_token"]})
    assert response.status_code == 200
    assert not web.cookies.get(cookie_name())

    web.cookies.set(cookie_name(), cookie)
    assert web.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": body["csrf_token"]}).status_code == 401


def test_silent_re_auth_works_after_the_cookie_is_gone(web) -> None:
    """Invariant 16: losing the cookie is a normal condition, not a failure. Fresh `initData`
    must produce a working session for the same account without any user-visible step."""
    telegram_id = new_telegram_id()
    first, _ = _sign_in(web, telegram_id)
    web.cookies.clear()

    second, _ = _sign_in(web, telegram_id)
    assert second["access_token"] != first["access_token"]

    me = web.get("/api/v1/users/me", headers={"Authorization": f"Bearer {second['access_token']}"})
    assert me.json()["username"] == f"tg_{telegram_id}"


def test_password_endpoints_are_gone(client) -> None:
    """D-10: no register, no login, no password-based Telegram linking."""
    # 404, not 405: the paths are gone entirely, so there is no route left to reject a method on.
    assert client.post("/api/v1/auth/register", json={"username": "x", "password": "y" * 12}).status_code == 404
    assert client.post("/api/v1/auth/login", json={"username": "x", "password": "y"}).status_code == 404
    assert client.post("/api/v1/users/me/link-telegram", json={"telegram_id": 1, "chat_id": 1}).status_code == 404


def test_users_me_requires_auth(client) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_update_profile(client, auth_headers) -> None:
    response = client.patch(
        "/api/v1/users/me",
        json={"height_cm": 178.5, "weight_kg": 74.2, "goal": "gain_muscle"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profile"]["height_cm"] == 178.5
    assert body["profile"]["goal"] == "gain_muscle"


def test_bot_door_requires_the_shared_secret(client) -> None:
    """D-20: /auth/telegram takes a telegram_id on trust, so the secret is the only thing
    standing between it and anyone who can reach the endpoint."""
    tg_id = new_telegram_id()
    payload = {"telegram_id": tg_id, "chat_id": tg_id}

    assert client.post("/api/v1/auth/telegram", json=payload).status_code == 401
    assert client.post("/api/v1/auth/telegram", json=payload, headers={"X-Bot-Secret": "wrong"}).status_code == 401

    ok = client.post("/api/v1/auth/telegram", json=payload, headers=BOT_HEADERS)
    assert ok.status_code == 200, ok.text
    # The bot has no cookie jar, so it receives the refresh token in the body instead (D-13).
    assert ok.json()["access_token"] and ok.json()["refresh_token"]
