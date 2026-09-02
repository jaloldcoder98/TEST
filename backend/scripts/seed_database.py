"""Seeds baseline reference data that isn't part of the exercise dataset itself: the default
public workout templates (spec §9 — Push/Pull/Legs/Upper/Lower/Full Body). Run after
`import_exercises.py`. Idempotent — upserts by (name, category).

Usage:
    python scripts/seed_database.py
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import async_session_factory  # noqa: E402
from app.models import WorkoutTemplate  # noqa: E402
from app.models.enums import WorkoutCategory  # noqa: E402

DEFAULT_TEMPLATES = [
    (WorkoutCategory.PUSH, "Push Day", "Chest, shoulders, triceps."),
    (WorkoutCategory.PULL, "Pull Day", "Back, biceps."),
    (WorkoutCategory.LEGS, "Leg Day", "Quads, hamstrings, glutes, calves."),
    (WorkoutCategory.UPPER, "Upper Body", "Full upper body — push and pull combined."),
    (WorkoutCategory.LOWER, "Lower Body", "Full lower body."),
    (WorkoutCategory.FULL_BODY, "Full Body", "Balanced full-body session."),
]


async def seed() -> None:
    async with async_session_factory() as session:
        created = 0
        for category, name, description in DEFAULT_TEMPLATES:
            result = await session.execute(
                select(WorkoutTemplate).where(WorkoutTemplate.name == name, WorkoutTemplate.category == category)
            )
            if result.scalar_one_or_none() is not None:
                continue
            session.add(
                WorkoutTemplate(name=name, description=description, category=category, is_public=True, created_by=None)
            )
            created += 1
        await session.commit()
    print(f"Seeded {created} new workout templates ({len(DEFAULT_TEMPLATES) - created} already existed).")


if __name__ == "__main__":
    asyncio.run(seed())
