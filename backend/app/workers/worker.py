"""ARQ worker entrypoint. Empty task list for now — Phase 4+ adds real background jobs here
(AI food-image analysis, nutrition_daily rollups, notification delivery, ...).
"""

from arq.connections import RedisSettings

from app.core.config import get_settings

settings = get_settings()


async def noop(ctx: dict) -> str:
    """Placeholder task so the worker has at least one registered function; remove once real
    jobs are added."""
    return "ok"


class WorkerSettings:
    functions = [noop]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
