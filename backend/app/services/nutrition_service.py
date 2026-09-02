"""Manual food logging (Phase 4c). AI photo analysis (`POST /nutrition/analyze-image`, Phase 7)
will feed the same `FoodLogCreateRequest` shape once an AIProvider is configured — until then the
client supplies name/grams/macros directly, same as any manual diet-tracking app.

`NutritionDaily` is a rolled-up per user per day cache so the dashboard never has to re-sum
`food_logs` on every load (docs/DATABASE.md). It's kept in sync here, in the same transaction as
the food log write, rather than recomputed lazily.
"""

import uuid
from datetime import date as date_

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ForbiddenError, NotFoundError
from app.models import FoodLog, FoodLogItem, NutritionDaily, User
from app.schemas.nutrition import DailyNutritionOut, FoodLogCreateRequest


async def _get_or_create_daily(db: AsyncSession, user_id: uuid.UUID, day: date_) -> NutritionDaily:
    result = await db.execute(select(NutritionDaily).where(NutritionDaily.user_id == user_id, NutritionDaily.date == day))
    daily = result.scalar_one_or_none()
    if daily is None:
        daily = NutritionDaily(user_id=user_id, date=day)
        db.add(daily)
        await db.flush()
    return daily


def _apply_calorie_target(daily: NutritionDaily, user: User) -> None:
    target = user.profile.daily_calorie_target if user.profile else None
    daily.remaining_calories = (target - daily.total_calories) if target is not None else None


async def create_food_log(db: AsyncSession, user: User, data: FoodLogCreateRequest) -> FoodLog:
    log_date = data.date or date_.today()

    total_calories = sum(item.calories for item in data.items)
    total_protein = sum(item.protein_g for item in data.items)
    total_carbs = sum(item.carbs_g for item in data.items)
    total_fat = sum(item.fat_g for item in data.items)

    food_log = FoodLog(
        user_id=user.id,
        date=log_date,
        meal_type=data.meal_type,
        description=data.description,
        total_calories=total_calories,
        protein_g=total_protein,
        carbs_g=total_carbs,
        fat_g=total_fat,
    )
    db.add(food_log)
    await db.flush()

    for item in data.items:
        db.add(
            FoodLogItem(
                food_log_id=food_log.id,
                food_item_id=item.food_item_id,
                name=item.name,
                estimated_grams=item.estimated_grams,
                calories=item.calories,
                protein_g=item.protein_g,
                carbs_g=item.carbs_g,
                fat_g=item.fat_g,
                confidence=item.confidence,
            )
        )

    daily = await _get_or_create_daily(db, user.id, log_date)
    daily.total_calories += total_calories
    daily.protein_g += total_protein
    daily.carbs_g += total_carbs
    daily.fat_g += total_fat
    _apply_calorie_target(daily, user)

    await db.flush()
    return await _get_owned_food_log(db, user.id, food_log.id)


async def _get_owned_food_log(db: AsyncSession, user_id: uuid.UUID, food_log_id: uuid.UUID) -> FoodLog:
    result = await db.execute(
        select(FoodLog).options(selectinload(FoodLog.items)).where(FoodLog.id == food_log_id)
    )
    food_log = result.scalar_one_or_none()
    if food_log is None:
        raise NotFoundError("FOOD_LOG_NOT_FOUND", "Food log not found")
    if food_log.user_id != user_id:
        raise ForbiddenError("This food log belongs to another user")
    return food_log


async def get_daily(db: AsyncSession, user: User, day: date_) -> DailyNutritionOut:
    result = await db.execute(
        select(FoodLog)
        .options(selectinload(FoodLog.items))
        .where(FoodLog.user_id == user.id, FoodLog.date == day)
        .order_by(FoodLog.created_at)
    )
    logs = list(result.scalars().unique().all())

    daily_result = await db.execute(select(NutritionDaily).where(NutritionDaily.user_id == user.id, NutritionDaily.date == day))
    daily = daily_result.scalar_one_or_none()

    target = user.profile.daily_calorie_target if user.profile else None
    total_calories = daily.total_calories if daily else 0.0
    return DailyNutritionOut(
        date=day,
        total_calories=total_calories,
        protein_g=daily.protein_g if daily else 0.0,
        carbs_g=daily.carbs_g if daily else 0.0,
        fat_g=daily.fat_g if daily else 0.0,
        calorie_target=target,
        remaining_calories=(target - total_calories) if target is not None else None,
        logs=logs,
    )


async def get_history(db: AsyncSession, user: User, date_from: date_, date_to: date_) -> list[DailyNutritionOut]:
    result = await db.execute(
        select(NutritionDaily)
        .where(NutritionDaily.user_id == user.id, NutritionDaily.date >= date_from, NutritionDaily.date <= date_to)
        .order_by(NutritionDaily.date)
    )
    dailies = {d.date: d for d in result.scalars().all()}

    logs_result = await db.execute(
        select(FoodLog)
        .options(selectinload(FoodLog.items))
        .where(FoodLog.user_id == user.id, FoodLog.date >= date_from, FoodLog.date <= date_to)
        .order_by(FoodLog.date, FoodLog.created_at)
    )
    logs_by_date: dict[date_, list[FoodLog]] = {}
    for log in logs_result.scalars().unique().all():
        logs_by_date.setdefault(log.date, []).append(log)

    target = user.profile.daily_calorie_target if user.profile else None
    out = []
    for day in sorted(set(dailies) | set(logs_by_date)):
        daily = dailies.get(day)
        total_calories = daily.total_calories if daily else 0.0
        out.append(
            DailyNutritionOut(
                date=day,
                total_calories=total_calories,
                protein_g=daily.protein_g if daily else 0.0,
                carbs_g=daily.carbs_g if daily else 0.0,
                fat_g=daily.fat_g if daily else 0.0,
                calorie_target=target,
                remaining_calories=(target - total_calories) if target is not None else None,
                logs=logs_by_date.get(day, []),
            )
        )
    return out
