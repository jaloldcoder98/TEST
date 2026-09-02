"""Workout session lifecycle: start -> log sets -> finish (compute totals + detect PRs).

Calorie estimation is a rough, clearly-labeled approximation (spec.md §13: never present as
medical advice) — not a substitute for a real MET-based model, which is a reasonable Phase 9+
refinement once real usage data exists.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.models import PersonalRecord, Workout, WorkoutExercise, WorkoutSession, WorkoutSet
from app.models.enums import RecordType, SessionStatus

# Rough estimate: ~0.1 kcal per kg of volume moved, plus a base rate per minute of session time.
# Deliberately simple and documented as an approximation — see module docstring.
CALORIES_PER_KG_VOLUME = 0.1
CALORIES_PER_MINUTE_BASE = 5


async def start_session(db: AsyncSession, user_id: uuid.UUID, workout_id: uuid.UUID) -> WorkoutSession:
    workout = (
        await db.execute(select(Workout).where(Workout.id == workout_id, Workout.user_id == user_id))
    ).scalar_one_or_none()
    if workout is None:
        raise NotFoundError("WORKOUT_NOT_FOUND", "Workout not found")

    session = WorkoutSession(
        user_id=user_id, workout_id=workout_id, status=SessionStatus.IN_PROGRESS, started_at=datetime.now(timezone.utc)
    )
    db.add(session)
    await db.flush()
    # Eager-load `sets` (empty at this point) so response-model serialization never touches the
    # lazy relationship outside an active session context (see docs/DATABASE.md / the
    # MissingGreenlet note in app/core/deps.py for why that matters under AsyncSession).
    return await _get_owned_session(db, user_id, session.id)


async def _get_owned_session(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> WorkoutSession:
    result = await db.execute(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .where(WorkoutSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise NotFoundError("SESSION_NOT_FOUND", "Workout session not found")
    if session.user_id != user_id:
        raise ForbiddenError("This workout session belongs to another user")
    return session


async def log_set(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID, data: dict) -> WorkoutSet:
    session = await _get_owned_session(db, user_id, session_id)
    if session.status != SessionStatus.IN_PROGRESS:
        raise AppError("SESSION_NOT_ACTIVE", "This session is not in progress", 409)

    workout_set = WorkoutSet(workout_session_id=session.id, **data)
    db.add(workout_set)
    await db.flush()
    return workout_set


async def finish_session(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> WorkoutSession:
    session = await _get_owned_session(db, user_id, session_id)
    if session.status == SessionStatus.COMPLETED:
        return session

    completed_sets = [s for s in session.sets if s.completed]
    total_sets = len(completed_sets)
    total_reps = sum(s.reps or 0 for s in completed_sets)
    total_volume = sum((s.weight_kg or 0) * (s.reps or 0) for s in completed_sets)

    finished_at = datetime.now(timezone.utc)
    duration_minutes = max(1, int((finished_at - session.started_at).total_seconds() // 60))
    estimated_calories = int(total_volume * CALORIES_PER_KG_VOLUME + duration_minutes * CALORIES_PER_MINUTE_BASE)

    session.status = SessionStatus.COMPLETED
    session.finished_at = finished_at
    session.total_sets = total_sets
    session.total_reps = total_reps
    session.total_volume_kg = total_volume
    session.estimated_calories = estimated_calories

    await _detect_personal_records(db, user_id, session, completed_sets)
    await db.flush()
    return session


async def _detect_personal_records(db: AsyncSession, user_id: uuid.UUID, session: WorkoutSession, completed_sets: list[WorkoutSet]) -> None:
    if not completed_sets:
        return

    # workout_exercise_id -> exercise_id, needed to attribute sets to an exercise for PR tracking.
    we_ids = {s.workout_exercise_id for s in completed_sets}
    result = await db.execute(select(WorkoutExercise).where(WorkoutExercise.id.in_(we_ids)))
    exercise_by_we_id = {we.id: we.exercise_id for we in result.scalars().all()}

    by_exercise: dict[uuid.UUID, list[WorkoutSet]] = {}
    for s in completed_sets:
        exercise_id = exercise_by_we_id.get(s.workout_exercise_id)
        if exercise_id:
            by_exercise.setdefault(exercise_id, []).append(s)

    for exercise_id, sets in by_exercise.items():
        candidates = {
            RecordType.MAX_WEIGHT: max((s.weight_kg or 0, s) for s in sets),
            RecordType.MAX_REPS: max((s.reps or 0, s) for s in sets),
            RecordType.MAX_VOLUME: max(((s.weight_kg or 0) * (s.reps or 0), s) for s in sets),
        }
        for record_type, (value, best_set) in candidates.items():
            if value <= 0:
                continue
            existing = (
                await db.execute(
                    select(PersonalRecord).where(
                        PersonalRecord.user_id == user_id,
                        PersonalRecord.exercise_id == exercise_id,
                        PersonalRecord.record_type == record_type,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    PersonalRecord(
                        user_id=user_id, exercise_id=exercise_id, record_type=record_type,
                        value=value, achieved_at=session.finished_at, workout_set_id=best_set.id,
                    )
                )
            elif value > existing.value:
                existing.value = value
                existing.achieved_at = session.finished_at
                existing.workout_set_id = best_set.id
