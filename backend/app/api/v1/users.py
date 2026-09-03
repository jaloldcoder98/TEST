# TODO(webapp-first): TZ §14 — the 12-step onboarding needs POST /users/me/onboarding: accepts the wizard answers
# in one call, computes BMR (Mifflin-St Jeor), TDEE and the macro split, persists them, and
# marks onboarding_completed. There is no BMR/TDEE code anywhere in the project today, so
# app/services/onboarding_service.py has to be written for it.
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import TelegramLinkRequest, UserOut, UserUpdateRequest
from app.services import auth_service

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    for field in ("first_name", "last_name", "language"):
        value = getattr(data, field)
        if value is not None:
            setattr(user, field, value)

    profile = user.profile
    for field in (
        "date_of_birth",
        "gender",
        "height_cm",
        "weight_kg",
        "goal",
        "experience_level",
        "activity_level",
        "daily_calorie_target",
        "protein_target_g",
        "carbs_target_g",
        "fat_target_g",
    ):
        value = getattr(data, field)
        if value is not None:
            setattr(profile, field, value)

    await db.flush()
    repo = UserRepository(db)
    return await repo.get_by_id(user.id)


@router.post("/me/link-telegram")
async def link_telegram(
    data: TelegramLinkRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    await auth_service.link_telegram(db, user.id, data.telegram_id, data.chat_id, data.telegram_username)
    return {"success": True}
