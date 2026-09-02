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


class TelegramLinkRequest(BaseModel):
    """POST /users/me/link-telegram — attaches a Telegram account to the *currently
    authenticated* user (after the bot has verified their username/password via POST
    /auth/login), so a user who registered on the web can use the same account in the bot."""

    telegram_id: int
    chat_id: int
    telegram_username: str | None = None


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
    daily_calorie_target: int | None = None
    protein_target_g: int | None = None
    carbs_target_g: int | None = None
    fat_target_g: int | None = None
