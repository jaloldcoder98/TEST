# TODO(webapp-first): TZ §17/§20 — analyze_image() accepts only a JSON `image_url`, so a phone camera capture
# has nowhere to go. Add a multipart upload variant that stores the file via a (still to be
# written) storage_service and feeds the vision model from there.
#
# TZ §33 — the AI must identify the food, not be the nutrition database. Today its calorie
# and macro numbers are returned to the user verbatim. Long term those should be looked up
# in a real food database; see audit §6.4 for the staged plan (ship with AI estimates clearly
# labelled approximate, add the database as its own phase).
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

from datetime import date as date_

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.ai import AIFoodAnalysisResult, FoodAnalysisRequest
from app.schemas.nutrition import DailyNutritionOut, FoodLogCreateRequest, FoodLogOut
from app.services import ai_service, nutrition_service

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


@router.post("/analyze-image", response_model=AIFoodAnalysisResult)
async def analyze_image(data: FoodAnalysisRequest, user: User = Depends(get_current_user)) -> AIFoodAnalysisResult:
    # Same pipeline as POST /ai/food-analysis (docs/API.md), exposed here too since this is where
    # a web/bot client naturally looks for it alongside manual logging. ai_service raises a clear
    # 503 AI_NOT_CONFIGURED itself when no AI provider is set up — nothing to fake here even
    # without a key (spec.md §61: no mock data in production paths). The result is a *suggestion*
    # for the user to review, not an auto-saved log — POST /nutrition/log still requires their
    # confirmation.
    return await ai_service.analyze_food_image(data)
