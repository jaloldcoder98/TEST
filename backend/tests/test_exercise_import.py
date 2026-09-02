"""Sanity check that the exercise import actually landed real data.

This intentionally reads whatever Postgres `DATABASE_URL` points to rather than spinning up an
isolated fixture DB — Phase 8 replaces this with a proper test-database fixture (a fresh schema
per test run). For now it's a fast, honest signal that `scripts/import_exercises.py` did what it
claims, and is skipped automatically if no exercises have been imported yet (e.g. in CI before
the seed step runs).
"""

import pytest
from sqlalchemy import func, select

from app.core.db import async_session_factory
from app.models import Exercise, ExerciseTranslation
from app.models.enums import Language


@pytest.mark.asyncio
async def test_exercises_imported() -> None:
    async with async_session_factory() as session:
        count = (await session.execute(select(func.count()).select_from(Exercise))).scalar_one()
        if count == 0:
            pytest.skip("No exercises imported yet — run `python scripts/import_exercises.py` first")

        assert count == 1323

        translated = (
            await session.execute(
                select(func.count())
                .select_from(ExerciseTranslation)
                .where(ExerciseTranslation.language == Language.EN)
            )
        ).scalar_one()
        assert translated == count  # every exercise has an EN translation

        ru_translated = (
            await session.execute(
                select(func.count())
                .select_from(ExerciseTranslation)
                .where(ExerciseTranslation.language == Language.RU)
            )
        ).scalar_one()
        assert ru_translated == 0  # importer must never fabricate ru/uz (spec.md §6)
