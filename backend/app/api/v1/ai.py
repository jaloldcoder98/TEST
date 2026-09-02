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
