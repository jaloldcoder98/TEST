"""services.session.call_authed is what lets every handler ignore token expiry entirely — it's
the single place that recovers from a stale access token (via refresh) or a stale refresh token
(via a full re-auth), so it's worth testing in isolation from any one handler."""

from __future__ import annotations

import pytest

from services.api_client import BackendAPIError
from services import session as session_module
from services.session import call_authed, ensure_session, get_language, set_language


class FakeBackend:
    """Stands in for services.api_client.backend. `telegram_auth` and `refresh` just hand back
    new tokens; test methods can be swapped per-test to simulate a failing call."""

    def __init__(self) -> None:
        self.telegram_auth_calls = 0
        self.refresh_calls = 0

    async def telegram_auth(self, telegram_id, chat_id, username, first_name, language):
        self.telegram_auth_calls += 1
        return {"access_token": f"access-{self.telegram_auth_calls}", "refresh_token": f"refresh-{self.telegram_auth_calls}"}

    async def refresh(self, refresh_token: str):
        self.refresh_calls += 1
        if refresh_token.startswith("dead"):
            raise BackendAPIError("UNAUTHORIZED", "Refresh token invalid", 401)
        return {"access_token": "access-refreshed", "refresh_token": "refresh-refreshed"}


@pytest.fixture
def fake_backend(monkeypatch):
    fb = FakeBackend()
    monkeypatch.setattr(session_module, "backend", fb)
    return fb


async def test_ensure_session_authenticates_once_and_caches(fake_backend):
    s1 = await ensure_session(42, 42, "bek", "Bek", "uz")
    s2 = await ensure_session(42, 42, "bek", "Bek", "uz")
    assert s1 is s2  # cached, no second telegram_auth call
    assert fake_backend.telegram_auth_calls == 1
    assert get_language(42) == "uz"


async def test_set_language_updates_cached_session(fake_backend):
    await ensure_session(42, 42, "bek", "Bek", "uz")
    set_language(42, "ru")
    assert get_language(42) == "ru"


async def test_get_language_defaults_when_no_session():
    assert get_language(9999) == "uz"
    assert get_language(9999, default="en") == "en"


async def test_call_authed_returns_result_when_token_is_valid(fake_backend):
    async def fn(token: str) -> str:
        assert token == "access-1"
        return "ok"

    result = await call_authed(42, 42, "bek", "Bek", "uz", fn)
    assert result == "ok"


async def test_call_authed_recovers_via_refresh_on_401(fake_backend):
    await ensure_session(42, 42, "bek", "Bek", "uz")  # seeds access-1 / refresh-1

    calls: list[str] = []

    async def fn(token: str) -> str:
        calls.append(token)
        if token == "access-1":
            raise BackendAPIError("UNAUTHORIZED", "Expired", 401)
        return "recovered"

    result = await call_authed(42, 42, "bek", "Bek", "uz", fn)

    assert result == "recovered"
    assert calls == ["access-1", "access-refreshed"]
    assert fake_backend.refresh_calls == 1
    assert fake_backend.telegram_auth_calls == 1  # no full re-auth needed


async def test_call_authed_falls_back_to_full_reauth_when_refresh_token_is_dead(fake_backend, monkeypatch):
    # Seed a session whose access token is stale and whose refresh token the fake backend rejects
    # outright — the only way back to a working session is a full re-auth.
    session_module.set_session(42, "access-stale", "dead-refresh", "uz")

    calls: list[str] = []

    async def fn(token: str) -> str:
        calls.append(token)
        if token == "access-stale":
            raise BackendAPIError("UNAUTHORIZED", "Expired", 401)
        return "recovered-via-reauth"

    result = await call_authed(42, 42, "bek", "Bek", "uz", fn)

    assert result == "recovered-via-reauth"
    assert calls == ["access-stale", "access-1"]  # "access-1" is the fake's first-ever telegram_auth token
    assert fake_backend.refresh_calls == 1
    assert fake_backend.telegram_auth_calls == 1  # the recovery re-auth (ensure_session's cache hit doesn't count again)


async def test_call_authed_reraises_non_401_errors_without_retrying(fake_backend):
    async def fn(token: str) -> str:
        raise BackendAPIError("WORKOUT_HAS_HISTORY", "Can't delete", 409)

    with pytest.raises(BackendAPIError) as exc_info:
        await call_authed(42, 42, "bek", "Bek", "uz", fn)
    assert exc_info.value.code == "WORKOUT_HAS_HISTORY"
    assert fake_backend.refresh_calls == 0
