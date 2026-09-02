"""Aggregates every /api/v1/* sub-router. Individual routers (auth, users, exercises, ...) are
added here as each is implemented in Phase 4 — this file is intentionally the single place that
wires the API surface together, so `docs/API.md` and the actual routes never silently drift.
"""

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", tags=["health"])
async def health() -> dict:
    return {"success": True, "status": "ok"}


# Phase 4 will add, in this order (see docs/IMPLEMENTATION_PLAN.md):
#   api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
#   api_router.include_router(users.router, prefix="/users", tags=["users"])
#   api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
#   api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
#   api_router.include_router(nutrition.router, prefix="/nutrition", tags=["nutrition"])
#   api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
#   api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
#   api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
