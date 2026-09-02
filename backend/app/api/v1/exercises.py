import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.core.errors import NotFoundError
from app.models import Exercise, Favorite, User
from app.models.enums import FavoritableType, Language
from app.repositories.exercise_repository import ExerciseRepository, pick_translation
from app.schemas.exercise import ExerciseDetail, ExerciseSummary, LookupOut, PaginatedExercises

router = APIRouter()
settings = get_settings()


async def _favorited_ids(db: AsyncSession, user: User | None, exercise_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if user is None or not exercise_ids:
        return set()
    result = await db.execute(
        select(Favorite.favoritable_id).where(
            Favorite.user_id == user.id,
            Favorite.favoritable_type == FavoritableType.EXERCISE.value,
            Favorite.favoritable_id.in_(exercise_ids),
        )
    )
    return set(result.scalars().all())


def _to_summary(exercise: Exercise, lang: Language, favorited_ids: set[uuid.UUID]) -> ExerciseSummary:
    translation = pick_translation(exercise, lang)
    return ExerciseSummary(
        id=exercise.id,
        slug=exercise.slug,
        name=translation.name,
        muscle=exercise.muscle.slug,
        body_part=exercise.body_part.slug,
        equipment=exercise.equipment.slug,
        category=exercise.category.slug,
        gif_url=exercise.gif_url,
        image_url=exercise.image_url,
        is_favorited=exercise.id in favorited_ids,
    )


@router.get("", response_model=PaginatedExercises)
async def list_exercises(
    muscle: str | None = None,
    equipment: str | None = None,
    bodyPart: str | None = None,
    category: str | None = None,
    q: str | None = None,
    lang: Language = Language.EN,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=None, ge=1, le=settings.max_page_size),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> PaginatedExercises:
    page_size = pageSize or settings.default_page_size
    repo = ExerciseRepository(db)
    items, total = await repo.list_paginated(
        page=page, page_size=page_size, muscle=muscle, equipment=equipment,
        body_part=bodyPart, category=category, q=q, lang=lang,
    )
    favorited = await _favorited_ids(db, user, [ex.id for ex in items])
    return PaginatedExercises(
        items=[_to_summary(ex, lang, favorited) for ex in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/search", response_model=PaginatedExercises)
async def search_exercises(
    q: str,
    lang: Language = Language.EN,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=None, ge=1, le=settings.max_page_size),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> PaginatedExercises:
    return await list_exercises(
        muscle=None, equipment=None, bodyPart=None, category=None, q=q, lang=lang,
        page=page, pageSize=pageSize, db=db, user=user,
    )


@router.get("/muscles", response_model=list[LookupOut])
async def list_muscles(db: AsyncSession = Depends(get_db)) -> list[LookupOut]:
    return [LookupOut(slug=slug, count=count) for slug, count in await ExerciseRepository(db).muscles()]


@router.get("/equipment", response_model=list[LookupOut])
async def list_equipment(db: AsyncSession = Depends(get_db)) -> list[LookupOut]:
    return [LookupOut(slug=slug, count=count) for slug, count in await ExerciseRepository(db).equipment_list()]


@router.get("/body-parts", response_model=list[LookupOut])
async def list_body_parts(db: AsyncSession = Depends(get_db)) -> list[LookupOut]:
    return [LookupOut(slug=slug, count=count) for slug, count in await ExerciseRepository(db).body_parts()]


@router.get("/categories", response_model=list[LookupOut])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[LookupOut]:
    return [LookupOut(slug=slug, count=count) for slug, count in await ExerciseRepository(db).categories()]


@router.get("/{exercise_id}", response_model=ExerciseDetail)
async def get_exercise(
    exercise_id: uuid.UUID,
    lang: Language = Language.EN,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> ExerciseDetail:
    exercise = await ExerciseRepository(db).get_by_id(exercise_id)
    if exercise is None:
        raise NotFoundError("EXERCISE_NOT_FOUND", "Exercise not found")

    translation = pick_translation(exercise, lang)
    favorited = await _favorited_ids(db, user, [exercise.id])
    return ExerciseDetail(
        id=exercise.id,
        slug=exercise.slug,
        name=translation.name,
        muscle=exercise.muscle.slug,
        body_part=exercise.body_part.slug,
        equipment=exercise.equipment.slug,
        category=exercise.category.slug,
        gif_url=exercise.gif_url,
        image_url=exercise.image_url,
        is_favorited=exercise.id in favorited,
        secondary_muscles=exercise.secondary_muscles,
        instructions=translation.instructions,
        source=exercise.source,
        source_url=exercise.source_url,
        is_machine_translated=translation.is_machine_translated,
    )


@router.post("/{exercise_id}/favorite")
async def favorite_exercise(
    exercise_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    exercise = await ExerciseRepository(db).get_by_id(exercise_id)
    if exercise is None:
        raise NotFoundError("EXERCISE_NOT_FOUND", "Exercise not found")

    existing = await db.execute(
        select(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.favoritable_type == FavoritableType.EXERCISE.value,
            Favorite.favoritable_id == exercise_id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(Favorite(user_id=user.id, favoritable_type=FavoritableType.EXERCISE.value, favoritable_id=exercise_id))
    return {"success": True}


@router.delete("/{exercise_id}/favorite")
async def unfavorite_exercise(
    exercise_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.favoritable_type == FavoritableType.EXERCISE.value,
            Favorite.favoritable_id == exercise_id,
        )
    )
    favorite = result.scalar_one_or_none()
    if favorite is not None:
        await db.delete(favorite)
    return {"success": True}
