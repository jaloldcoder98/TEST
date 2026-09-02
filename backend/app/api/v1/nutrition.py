from datetime import date as date_

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.models import User
from app.schemas.nutrition import DailyNutritionOut, FoodLogCreateRequest, FoodLogOut
from app.services import nutrition_service

router = APIRouter()


@router.post("/log", response_model=FoodLogOut)
async def log_food(
    data: FoodLogCreateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> FoodLogOut:
    return await nutrition_service.create_food_log(db, user, data)


@router.get("/today", response_model=DailyNutritionOut)
async def get_today(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DailyNutritionOut:
    return await nutrition_service.get_daily(db, user, date_.today())


@router.get("/history", response_model=list[DailyNutritionOut])
async def get_history(
    date_from: date_ = Query(alias="from"),
    date_to: date_ = Query(alias="to"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DailyNutritionOut]:
    return await nutrition_service.get_history(db, user, date_from, date_to)


@router.post("/analyze-image")
async def analyze_image(user: User = Depends(get_current_user)) -> dict:
    # Route exists to match docs/API.md's documented surface, but AI food-photo analysis is
    # Phase 7 (blocked on an OpenAI key not yet provided) — this responds honestly instead of a
    # generic 404 or (worse) a fake result, per spec.md §61 "no mock data in production paths".
    raise AppError(
        "AI_NOT_CONFIGURED",
        "AI food analysis isn't available yet. Log the meal manually using POST /nutrition/log for now.",
        503,
    )
