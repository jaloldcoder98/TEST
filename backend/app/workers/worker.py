# TODO(webapp-first): TZ §25 — this is where the reminder pipeline goes, and it is still the placeholder it
# shipped as. Needed: ARQ cron jobs for workout / nutrition / weekly-progress reminders that
# respect each user's notification settings, plus a delivery path to the bot. Nothing in the
# product sends a single notification today.
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

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
