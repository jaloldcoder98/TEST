"""Imports the ExerciseGymGifsDB dataset (data/exercises/exercises.en.json, a snapshot of the
source repo's `api/en/exercises.json` — see docs/ARCHITECTURE.md §1) into Postgres.

Idempotent: safe to re-run — upserts lookups and exercises by their natural keys
(slug / external_id) rather than inserting duplicates.

Deliberately does NOT populate `ru`/`uz` exercise_translations — per spec §6, translations are
never auto-generated during import. Only `en` is seeded here; `ru`/`uz` rows are added later
through the admin enrichment workflow (docs/ARCHITECTURE.md §5).

Usage:
    python scripts/import_exercises.py [--file path/to/exercises.en.json]
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import async_session_factory  # noqa: E402
from app.models import BodyPart, Category, Equipment, Exercise, ExerciseTranslation, Muscle  # noqa: E402
from app.models.enums import Language  # noqa: E402

DEFAULT_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "exercises" / "exercises.en.json"
SOURCE_NAME = "exercisegymgifsdb"
SOURCE_REPO_URL = "https://github.com/JahelCuadrado/ExerciseGymGifsDB"


async def get_or_create_lookup(session: AsyncSession, model, slug: str, sort_order: int) -> object:
    result = await session.execute(select(model).where(model.slug == slug))
    row = result.scalar_one_or_none()
    if row is None:
        row = model(slug=slug, sort_order=sort_order)
        session.add(row)
        await session.flush()  # assigns row.id without committing
    return row


async def import_exercises(data_file: Path) -> None:
    payload = json.loads(data_file.read_text(encoding="utf-8"))
    exercises = payload["exercises"]
    print(f"Loaded {len(exercises)} exercises from {data_file}")

    async with async_session_factory() as session:
        muscle_cache: dict[str, Muscle] = {}
        body_part_cache: dict[str, BodyPart] = {}
        equipment_cache: dict[str, Equipment] = {}
        category_cache: dict[str, Category] = {}

        created, updated = 0, 0

        for i, ex in enumerate(exercises):
            muscle_slug = ex["muscle"]
            body_part_slug = ex["bodyPart"]
            equipment_slug = ex["equipment"]
            category_slug = ex["category"]

            if muscle_slug not in muscle_cache:
                muscle_cache[muscle_slug] = await get_or_create_lookup(session, Muscle, muscle_slug, len(muscle_cache))
            if body_part_slug not in body_part_cache:
                body_part_cache[body_part_slug] = await get_or_create_lookup(
                    session, BodyPart, body_part_slug, len(body_part_cache)
                )
            if equipment_slug not in equipment_cache:
                equipment_cache[equipment_slug] = await get_or_create_lookup(
                    session, Equipment, equipment_slug, len(equipment_cache)
                )
            if category_slug not in category_cache:
                category_cache[category_slug] = await get_or_create_lookup(
                    session, Category, category_slug, len(category_cache)
                )

            external_id = ex["id"]  # e.g. "biceps/barbell-curl"
            result = await session.execute(select(Exercise).where(Exercise.external_id == external_id))
            exercise = result.scalar_one_or_none()

            if exercise is None:
                exercise = Exercise(
                    external_id=external_id,
                    slug=ex["slug"],
                    source=SOURCE_NAME,
                    source_url=SOURCE_REPO_URL,
                )
                session.add(exercise)
                created += 1
            else:
                updated += 1

            exercise.muscle = muscle_cache[muscle_slug]
            exercise.body_part = body_part_cache[body_part_slug]
            exercise.equipment = equipment_cache[equipment_slug]
            exercise.category = category_cache[category_slug]
            exercise.secondary_muscles = ex.get("secondaryMuscles", [])
            exercise.gif_url = ex["gifUrl"]
            exercise.image_url = ex.get("thumbUrl")

            await session.flush()  # assigns exercise.id if newly created

            result = await session.execute(
                select(ExerciseTranslation).where(
                    ExerciseTranslation.exercise_id == exercise.id,
                    ExerciseTranslation.language == Language.EN,
                )
            )
            translation = result.scalar_one_or_none()
            if translation is None:
                translation = ExerciseTranslation(exercise_id=exercise.id, language=Language.EN)
                session.add(translation)
            translation.name = ex["name"]
            translation.instructions = ex.get("instructions", [])
            translation.is_machine_translated = False  # this is the dataset's authored EN text

            if (i + 1) % 200 == 0:
                print(f"  ...{i + 1}/{len(exercises)}")

        await session.commit()

    print(f"Done. {created} exercises created, {updated} updated.")
    print(
        f"Lookups: {len(muscle_cache)} muscles, {len(body_part_cache)} body parts, "
        f"{len(equipment_cache)} equipment, {len(category_cache)} categories."
    )
    print("Note: ru/uz translations were NOT created — add them via the admin enrichment workflow.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT_DATA_FILE, help="Path to exercises.en.json")
    args = parser.parse_args()

    if not args.file.exists():
        raise SystemExit(f"Data file not found: {args.file}")

    asyncio.run(import_exercises(args.file))
