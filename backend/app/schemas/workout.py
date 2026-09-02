import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import SessionStatus, WorkoutCategory


class WorkoutExerciseIn(BaseModel):
    exercise_id: uuid.UUID
    order: int = 0
    notes: str | None = None


class WorkoutExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_id: uuid.UUID
    order: int
    notes: str | None


class WorkoutCreateRequest(BaseModel):
    name: str
    description: str | None = None
    day: str | None = None
    template_id: uuid.UUID | None = None
    exercises: list[WorkoutExerciseIn] = []


class WorkoutUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    day: str | None = None
    exercises: list[WorkoutExerciseIn] | None = None


class WorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    day: str | None
    duration_minutes: int | None
    exercises: list[WorkoutExerciseOut]


class WorkoutTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    category: WorkoutCategory
    is_public: bool


class WorkoutSetIn(BaseModel):
    workout_exercise_id: uuid.UUID
    set_number: int
    reps: int | None = None
    weight_kg: float | None = None
    duration_seconds: int | None = None
    rest_seconds: int | None = None
    completed: bool = False
    notes: str | None = None


class WorkoutSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workout_exercise_id: uuid.UUID
    set_number: int
    reps: int | None
    weight_kg: float | None
    duration_seconds: int | None
    rest_seconds: int | None
    completed: bool
    notes: str | None


class WorkoutSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workout_id: uuid.UUID
    status: SessionStatus
    started_at: datetime
    finished_at: datetime | None
    total_volume_kg: float | None
    total_sets: int | None
    total_reps: int | None
    estimated_calories: int | None
    sets: list[WorkoutSetOut] = []
