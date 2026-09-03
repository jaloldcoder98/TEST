# TODO(webapp-first): Audit §1.3 / TZ §32 — none of these endpoints is rate-limited, and the vision path
# (/nutrition/analyze-image, same service) is the most expensive call in the product.
# Needed: per-user daily quota, token + cost logging to an ai_usage table, and an admin
# read endpoint. The existing app/core/rate_limit.py is per-IP only — a per-user variant
# has to be added first.
#
# TZ §16 also asks for streamed AI responses: add POST /ai/chat/stream (SSE) alongside the
# existing buffered /ai/chat rather than replacing it.
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.ai import (
    AIFoodAnalysisResult,
    ChatRequest,
    ChatResponse,
    FoodAnalysisRequest,
    GeneratedWorkoutOut,
    WorkoutGenerateRequest,
)
from app.services import ai_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(data: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ChatResponse:
    return await ai_service.chat(db, user, data)


@router.post("/nutrition", response_model=ChatResponse)
async def nutrition_chat(
    data: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    return await ai_service.ask_nutrition(db, user, data)


@router.post("/workout", response_model=GeneratedWorkoutOut)
async def generate_workout(
    data: WorkoutGenerateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> GeneratedWorkoutOut:
    return await ai_service.generate_workout(db, user, data)


@router.post("/food-analysis", response_model=AIFoodAnalysisResult)
async def food_analysis(data: FoodAnalysisRequest, user: User = Depends(get_current_user)) -> AIFoodAnalysisResult:
    return await ai_service.analyze_food_image(data)
