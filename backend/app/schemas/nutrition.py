import uuid
from datetime import date as date_

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MealType


class FoodLogItemIn(BaseModel):
    name: str
    estimated_grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float | None = None
    food_item_id: uuid.UUID | None = None


class FoodLogCreateRequest(BaseModel):
    date: date_ | None = None  # defaults to today
    meal_type: MealType
    description: str | None = None
    items: list[FoodLogItemIn] = Field(min_length=1)


class FoodLogItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    estimated_grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float | None


class FoodLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: date_
    meal_type: MealType
    description: str | None
    image_url: str | None
    total_calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    ai_confidence: float | None
    items: list[FoodLogItemOut]


class DailyNutritionOut(BaseModel):
    date: date_
    total_calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    calorie_target: int | None
    remaining_calories: float | None
    logs: list[FoodLogOut]
