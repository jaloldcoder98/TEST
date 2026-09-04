"""Aggregates every /api/v1/* sub-router. Individual routers (auth, users, exercises, ...) are
added here as each is implemented in Phase 4 — this file is intentionally the single place that
wires the API surface together, so `docs/API.md` and the actual routes never silently drift.
"""

from fastapi import APIRouter

from app.api.v1 import ai, auth, exercises, nutrition, progress, users, workouts
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", tags=["health"])
async def health() -> dict:
    return {"success": True, "status": "ok"}


api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
api_router.include_router(workouts.router, tags=["workouts"])  # serves /workouts/* and /workout-sessions/*
api_router.include_router(nutrition.router, prefix="/nutrition", tags=["nutrition"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])

# Phase 0 only, and only ever in a debug process: the Telegram WebView diagnostics used to fill
# in docs/TELEGRAM_WEBVIEW_MATRIX.md. Mounting is conditional rather than guarded per-endpoint so
# that in production these routes do not exist at all — there is no handler to reach, no flag to
# get wrong. Deleted once Phase 0 is signed off.
if settings.debug:
    from app.api.v1 import diag  # noqa: E402 — deliberately not imported in a production process

    api_router.include_router(diag.router, prefix="/_diag", tags=["diagnostics"])

# Still to add (see docs/IMPLEMENTATION_PLAN.md Phase 3+):
#   api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
