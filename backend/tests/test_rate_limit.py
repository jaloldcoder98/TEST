"""app.core.rate_limit — brute-force protection on /auth/* (Phase 9 security audit / spec.md
§37). Rate limiting is force-disabled for the rest of this suite (tests/conftest.py sets
RATE_LIMIT_ENABLED=false before the app is imported, since every test shares one TestClient and
therefore one client IP) — these tests re-enable it deliberately and clean up after themselves so
nothing here leaks into other test files.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import redis as sync_redis

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import rate_limit


def _fake_request(ip: str = "203.0.113.5") -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host=ip))


@pytest.fixture(autouse=True)
def _enabled_and_clean():
    import app.core.rate_limit as rate_limit_module

    settings = get_settings()
    original = settings.rate_limit_enabled
    settings.rate_limit_enabled = True

    # app.core.rate_limit's async Redis client is cached at module scope for the app's real
    # lifetime (one event loop, forever). Different tests below run on different event loops —
    # pytest-asyncio's own per-function loop for the async unit tests, the TestClient's separate
    # persistent portal loop for the end-to-end HTTP test — so a cached client from one test would
    # be bound to an already-closed loop by the time the next test uses it ("attached to a
    # different loop"). Resetting the cache here (with a plain *sync* Redis client doing the
    # cleanup, entirely outside of asyncio) means each test's first call to the app's async client
    # always creates a fresh one bound to whatever loop is actually running at that moment.
    rate_limit_module._redis_client = None

    sync_client = sync_redis.from_url(get_settings().redis_url, decode_responses=True)
    for key in sync_client.scan_iter("ratelimit:test_*"):
        sync_client.delete(key)
    for key in sync_client.scan_iter("ratelimit:login:*"):
        sync_client.delete(key)
    sync_client.close()

    yield

    settings.rate_limit_enabled = original
    rate_limit_module._redis_client = None


@pytest.mark.asyncio
async def test_allows_requests_under_the_limit():
    dependency = rate_limit("test_under", max_requests=3, window_seconds=60)
    request = _fake_request()
    for _ in range(3):
        await dependency(request)  # no exception


@pytest.mark.asyncio
async def test_blocks_once_the_limit_is_exceeded():
    dependency = rate_limit("test_over", max_requests=3, window_seconds=60)
    request = _fake_request()
    for _ in range(3):
        await dependency(request)

    with pytest.raises(AppError) as exc_info:
        await dependency(request)
    assert exc_info.value.code == "RATE_LIMITED"
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_limits_are_scoped_per_client_ip():
    dependency = rate_limit("test_per_ip", max_requests=2, window_seconds=60)
    ip_a = _fake_request("203.0.113.10")
    ip_b = _fake_request("203.0.113.20")

    await dependency(ip_a)
    await dependency(ip_a)
    with pytest.raises(AppError):
        await dependency(ip_a)

    # A different IP has its own, untouched budget.
    await dependency(ip_b)
    await dependency(ip_b)


@pytest.mark.asyncio
async def test_limits_are_scoped_per_endpoint_key():
    login_limit = rate_limit("test_scope_login", max_requests=2, window_seconds=60)
    register_limit = rate_limit("test_scope_register", max_requests=2, window_seconds=60)
    request = _fake_request("203.0.113.30")

    await login_limit(request)
    await login_limit(request)
    with pytest.raises(AppError):
        await login_limit(request)

    # Exhausting "login" for this IP doesn't touch "register"'s separate budget.
    await register_limit(request)
    await register_limit(request)


@pytest.mark.asyncio
async def test_disabled_by_settings_never_blocks():
    settings = get_settings()
    settings.rate_limit_enabled = False
    try:
        dependency = rate_limit("test_disabled", max_requests=1, window_seconds=60)
        request = _fake_request()
        for _ in range(5):
            await dependency(request)  # never raises, even well past the nominal limit
    finally:
        settings.rate_limit_enabled = True


@pytest.mark.asyncio
async def test_fails_open_when_redis_is_unreachable(monkeypatch):
    import app.core.rate_limit as rate_limit_module

    class _BrokenRedis:
        async def incr(self, *_args, **_kwargs):
            raise ConnectionError("redis is down")

    monkeypatch.setattr(rate_limit_module, "_get_redis", lambda: _BrokenRedis())

    dependency = rate_limit("test_broken_redis", max_requests=1, window_seconds=60)
    request = _fake_request()
    for _ in range(5):
        await dependency(request)  # allowed through despite being well past the limit


def test_login_endpoint_enforces_the_limit_end_to_end(client):
    for _ in range(10):
        response = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "wrong"})
        assert response.status_code != 429

    blocked = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "wrong"})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
