import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.models import User, Workout, WorkoutExercise, WorkoutSession
from app.schemas.workout import (
    WorkoutCreateRequest,
    WorkoutOut,
    WorkoutSessionOut,
    WorkoutSetIn,
    WorkoutSetOut,
    WorkoutUpdateRequest,
)
from app.services import workout_service

# Mounted with no prefix at the api_router level (see app/api/v1/router.py) since this module
# serves both /workouts/* and /workout-sessions/* per docs/API.md.
router = APIRouter()


async def _get_owned_workout(db: AsyncSession, user: User, workout_id: uuid.UUID) -> Workout:
    result = await db.execute(
        select(Workout).options(selectinload(Workout.exercises)).where(Workout.id == workout_id)
    )
    workout = result.scalar_one_or_none()
    if workout is None:
        raise NotFoundError("WORKOUT_NOT_FOUND", "Workout not found")
    if workout.user_id != user.id:
        raise ForbiddenError("This workout belongs to another user")
    return workout


@router.get("/workouts", response_model=list[WorkoutOut])
async def list_workouts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[Workout]:
    result = await db.execute(
        select(Workout).options(selectinload(Workout.exercises)).where(Workout.user_id == user.id).order_by(Workout.created_at.desc())
    )
    return list(result.scalars().unique().all())


@router.post("/workouts", response_model=WorkoutOut)
async def create_workout(
    data: WorkoutCreateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Workout:
    workout = Workout(user_id=user.id, name=data.name, description=data.description, day=data.day, template_id=data.template_id)
    db.add(workout)
    await db.flush()
    for ex in data.exercises:
        db.add(WorkoutExercise(workout_id=workout.id, exercise_id=ex.exercise_id, order=ex.order, notes=ex.notes))
    await db.flush()
    return await _get_owned_workout(db, user, workout.id)


@router.get("/workouts/{workout_id}", response_model=WorkoutOut)
async def get_workout(workout_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Workout:
    return await _get_owned_workout(db, user, workout_id)


@router.patch("/workouts/{workout_id}", response_model=WorkoutOut)
async def update_workout(
    workout_id: uuid.UUID, data: WorkoutUpdateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Workout:
    workout = await _get_owned_workout(db, user, workout_id)
    for field in ("name", "description", "day"):
        value = getattr(data, field)
        if value is not None:
            setattr(workout, field, value)

    if data.exercises is not None:
        for existing in list(workout.exercises):
            await db.delete(existing)
        await db.flush()
        for ex in data.exercises:
            db.add(WorkoutExercise(workout_id=workout.id, exercise_id=ex.exercise_id, order=ex.order, notes=ex.notes))

    await db.flush()
    return await _get_owned_workout(db, user, workout_id)


@router.delete("/workouts/{workout_id}")
async def delete_workout(workout_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    workout = await _get_owned_workout(db, user, workout_id)

    has_history = (
        await db.execute(select(WorkoutSession.id).where(WorkoutSession.workout_id == workout_id).limit(1))
    ).scalar_one_or_none()
    if has_history is not None:
        # Logged sets reference workout_exercises, which reference this workout — deleting it
        # would either violate that FK or destroy history that's supposed to be immutable
        # (docs/DATABASE.md). Archiving instead of hard-deleting is the Phase 5+ UI answer;
        # for now the API just refuses rather than silently losing data.
        raise AppError(
            "WORKOUT_HAS_HISTORY",
            "This workout has logged sessions and can't be deleted. Deactivate it instead.",
            409,
        )

    await db.delete(workout)
    return {"success": True}


@router.post("/workouts/{workout_id}/start", response_model=WorkoutSessionOut)
async def start_workout(workout_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await workout_service.start_session(db, user.id, workout_id)


@router.post("/workout-sessions/{session_id}/sets", response_model=WorkoutSetOut)
async def log_workout_set(
    session_id: uuid.UUID, data: WorkoutSetIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    payload = data.model_dump(exclude={"workout_exercise_id"})
    payload["workout_exercise_id"] = data.workout_exercise_id
    return await workout_service.log_set(db, user.id, session_id, payload)


@router.post("/workout-sessions/{session_id}/finish", response_model=WorkoutSessionOut)
async def finish_workout(session_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await workout_service.finish_session(db, user.id, session_id)
