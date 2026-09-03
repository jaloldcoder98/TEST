# TODO(webapp-first): Audit §1.3 — this limiter keys on client IP only. AI quotas have to be per *user* (TZ §32:
# per-user daily AI limit, per-user food-analysis limit), and behind a proxy every request
# can share one IP anyway. Add a user-keyed variant that reuses the same Redis backend.
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

"""Fixed-window rate limiting for the most abuse-sensitive endpoints — login, register, refresh,
and the Telegram auto-auth endpoint (spec.md §37: brute-force / credential-stuffing protection).

Backed by Redis (already a first-class dependency of this stack — see docker-compose.yml) rather
than an in-process counter, so the limit is shared across every backend replica instead of being
trivially bypassed by hitting a different pod/process. Counting is a simple INCR+EXPIRE fixed
window per (client IP, endpoint key) — not perfectly smooth at window boundaries, but simple,
auditable, and more than sufficient for the accounts this app protects.

Fails OPEN: if Redis is unreachable, the request is allowed through rather than taking the entire
auth surface down — a rate limiter should never itself become a single point of failure — but a
warning is logged so an operator notices Redis is down.
"""

import logging

from fastapi import Request
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None


def _get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis_client


def rate_limit(key: str, max_requests: int, window_seconds: int):
    """FastAPI dependency factory: `Depends(rate_limit("login", 20, 60))` allows at most
    `max_requests` calls per `window_seconds` seconds, per client IP, for this `key`."""

    async def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return

        client_ip = request.client.host if request.client else "unknown"
        redis_key = f"ratelimit:{key}:{client_ip}"

        try:
            redis = _get_redis()
            count = await redis.incr(redis_key)
            if count == 1:
                await redis.expire(redis_key, window_seconds)
        except Exception:
            logger.warning("Rate limiter: Redis unavailable, allowing request through (fail-open): %s", redis_key)
            return

        if count > max_requests:
            raise AppError(
                "RATE_LIMITED",
                "Too many requests. Please wait a moment and try again.",
                429,
            )

    return dependency
