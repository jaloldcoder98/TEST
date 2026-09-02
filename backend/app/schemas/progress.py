import uuid
from datetime import date as date_

from pydantic import BaseModel, ConfigDict


class WeightLogRequest(BaseModel):
    date: date_ | None = None  # defaults to today
    weight_kg: float


class MeasurementLogRequest(BaseModel):
    date: date_ | None = None  # defaults to today
    weight_kg: float | None = None
    body_fat_pct: float | None = None
    chest_cm: float | None = None
    waist_cm: float | None = None
    hips_cm: float | None = None
    arms_cm: float | None = None
    thighs_cm: float | None = None
    notes: str | None = None


class BodyMeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: date_
    weight_kg: float | None
    body_fat_pct: float | None
    chest_cm: float | None
    waist_cm: float | None
    hips_cm: float | None
    arms_cm: float | None
    thighs_cm: float | None
    notes: str | None


class WorkoutSessionPoint(BaseModel):
    date: date_
    total_volume_kg: float | None
    estimated_calories: int | None


class ProgressSummaryOut(BaseModel):
    weight_trend: list[BodyMeasurementOut]
    workout_count: int
    total_volume_kg: float
    volume_trend: list[WorkoutSessionPoint]
