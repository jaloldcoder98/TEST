"""Abuse throttling for repeated `initData` payloads (docs/DECISIONS.md D-17).

The distinction this module exists to preserve: **this is not a one-time nonce.** Telegram hands
the Mini App the same `initData` string for the life of a launch, so a reload, a re-auth after
the access token expires, or a flaky network retry all legitimately present a payload the server
has already seen. Rejecting the second sighting would break normal use while stopping an attacker
only until they captured a fresh string.

What it does instead is count sightings of one identical payload inside the freshness window and
refuse only once that count becomes absurd for a human — a signal of scripted replay, not of a
user reopening the app. Freshness (D-16) and the HMAC signature remain the real gates.

Fails open when Redis is unavailable: a degraded cache must never take authentication down.
"""

from __future__ import annotations

import hashlib
import logging

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)
settings = get_settings()

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


class InitDataAbuseError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "INIT_DATA_REPLAY_ABUSE",
            "This Telegram session data has been presented too many times — reopen the app",
            429,
        )


async def record_and_check(init_data: str) -> int:
    """Count this exact payload; raise once it crosses the abuse threshold. Returns the count."""
    if not init_data:
        return 0

    digest = hashlib.sha256(init_data.encode()).hexdigest()
    key = f"initdata:seen:{digest}"

    try:
        redis = _get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, settings.init_data_repeat_window_seconds)
    except Exception as exc:  # noqa: BLE001 — a cache outage must not break login
        logger.warning("initData repeat check unavailable, allowing request: %s", exc)
        return 0

    if count > settings.init_data_max_repeats:
        raise InitDataAbuseError()
    return count


async def reset(init_data: str) -> None:
    """Test helper: forget a payload's count so a suite can reuse one string."""
    digest = hashlib.sha256(init_data.encode()).hexdigest()
    try:
        await _get_redis().delete(f"initdata:seen:{digest}")
    except Exception:  # noqa: BLE001
        pass
