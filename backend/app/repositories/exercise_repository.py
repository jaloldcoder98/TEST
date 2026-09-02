import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import BodyPart, Category, Equipment, Exercise, ExerciseTranslation, Muscle
from app.models.enums import Language


class ExerciseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _base_query(self):
        return select(Exercise).options(
            selectinload(Exercise.muscle),
            selectinload(Exercise.body_part),
            selectinload(Exercise.equipment),
            selectinload(Exercise.category),
            selectinload(Exercise.translations),
        ).where(Exercise.is_active.is_(True))

    def _apply_filters(self, query, *, muscle=None, equipment=None, body_part=None, category=None, q=None, lang=Language.EN):
        if muscle:
            query = query.where(Exercise.muscle.has(Muscle.slug == muscle))
        if equipment:
            query = query.where(Exercise.equipment.has(Equipment.slug == equipment))
        if body_part:
            query = query.where(Exercise.body_part.has(BodyPart.slug == body_part))
        if category:
            query = query.where(Exercise.category.has(Category.slug == category))
        if q:
            # Search the requested language's translation; falls back to English since ru/uz
            # aren't seeded yet (docs/ARCHITECTURE.md §5) — once they are, this still works
            # unchanged for whichever languages have rows.
            query = query.where(
                Exercise.translations.any(
                    (ExerciseTranslation.language == lang) & ExerciseTranslation.name.ilike(f"%{q}%")
                )
                | Exercise.translations.any(
                    (ExerciseTranslation.language == Language.EN) & ExerciseTranslation.name.ilike(f"%{q}%")
                )
            )
        return query

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        muscle: str | None = None,
        equipment: str | None = None,
        body_part: str | None = None,
        category: str | None = None,
        q: str | None = None,
        lang: Language = Language.EN,
    ) -> tuple[list[Exercise], int]:
        filtered = self._apply_filters(
            select(Exercise.id).where(Exercise.is_active.is_(True)),
            muscle=muscle, equipment=equipment, body_part=body_part, category=category, q=q, lang=lang,
        )
        total = (await self.db.execute(select(func.count()).select_from(filtered.subquery()))).scalar_one()

        query = self._apply_filters(
            self._base_query(), muscle=muscle, equipment=equipment, body_part=body_part, category=category, q=q, lang=lang
        )
        query = query.order_by(Exercise.slug).offset((page - 1) * page_size).limit(page_size)
        items = (await self.db.execute(query)).scalars().unique().all()
        return list(items), total

    async def get_by_id(self, exercise_id: uuid.UUID) -> Exercise | None:
        query = self._base_query().where(Exercise.id == exercise_id)
        return (await self.db.execute(query)).scalar_one_or_none()

    async def list_related(self, exercise: Exercise, limit: int = 6) -> list[Exercise]:
        query = (
            self._base_query()
            .where(Exercise.muscle_id == exercise.muscle_id, Exercise.id != exercise.id)
            .order_by(func.random())
            .limit(limit)
        )
        return list((await self.db.execute(query)).scalars().unique().all())

    async def muscles(self) -> list[tuple[str, int]]:
        return await self._lookup_counts(Muscle, Exercise.muscle_id)

    async def equipment_list(self) -> list[tuple[str, int]]:
        return await self._lookup_counts(Equipment, Exercise.equipment_id)

    async def body_parts(self) -> list[tuple[str, int]]:
        return await self._lookup_counts(BodyPart, Exercise.body_part_id)

    async def categories(self) -> list[tuple[str, int]]:
        return await self._lookup_counts(Category, Exercise.category_id)

    async def _lookup_counts(self, model, fk_column) -> list[tuple[str, int]]:
        query = (
            select(model.slug, func.count(Exercise.id))
            .select_from(Exercise)
            .join(model, fk_column == model.id)
            .where(Exercise.is_active.is_(True))
            .group_by(model.slug)
            .order_by(model.slug)
        )
        result = await self.db.execute(query)
        return [(row[0], row[1]) for row in result.all()]


def pick_translation(exercise: Exercise, lang: Language) -> ExerciseTranslation:
    """The requested language if present, else English (docs/ARCHITECTURE.md §5 — ru/uz aren't
    always seeded, and we never want to show a blank name)."""
    by_lang = {t.language: t for t in exercise.translations}
    return by_lang.get(lang) or by_lang.get(Language.EN) or exercise.translations[0]
