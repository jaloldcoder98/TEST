import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import ActivityLevel, ExperienceLevel, Gender, Goal, Language


class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_of_birth: date | None = None
    gender: Gender | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    goal: Goal | None = None
    experience_level: ExperienceLevel | None = None
    activity_level: ActivityLevel | None = None
    daily_calorie_target: int | None = None
    protein_target_g: int | None = None
    carbs_target_g: int | None = None
    fat_target_g: int | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str | None
    first_name: str | None
    last_name: str | None
    language: Language
    profile: UserProfileOut | None = None


class UserUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    language: Language | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    goal: Goal | None = None
    experience_level: ExperienceLevel | None = None
    activity_level: ActivityLevel | None = None
