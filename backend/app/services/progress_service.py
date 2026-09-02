"""Progress tracking (Phase 4d): body measurements (weight is just the common-case subset) plus a
dashboard summary that reads from workout_sessions for volume/frequency, so nothing here
duplicates data already computed by workout_service on session finish (docs/DATABASE.md).
"""

import uuid
from datetime import date as date_, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BodyMeasurement, WorkoutSession
from app.models.enums import SessionStatus
from app.schemas.progress import MeasurementLogRequest, ProgressSummaryOut, WeightLogRequest

DEFAULT_SUMMARY_WINDOW_DAYS = 90


async def _get_or_create_measurement(db: AsyncSession, user_id: uuid.UUID, day: date_) -> BodyMeasurement:
    result = await db.execute(select(BodyMeasurement).where(BodyMeasurement.user_id == user_id, BodyMeasurement.date == day))
    measurement = result.scalar_one_or_none()
    if measurement is None:
        measurement = BodyMeasurement(user_id=user_id, date=day)
        db.add(measurement)
        await db.flush()
    return measurement


async def log_weight(db: AsyncSession, user_id: uuid.UUID, data: WeightLogRequest) -> BodyMeasurement:
    day = data.date or date_.today()
    measurement = await _get_or_create_measurement(db, user_id, day)
    measurement.weight_kg = data.weight_kg
    await db.flush()
    return measurement


async def log_measurements(db: AsyncSession, user_id: uuid.UUID, data: MeasurementLogRequest) -> BodyMeasurement:
    day = data.date or date_.today()
    measurement = await _get_or_create_measurement(db, user_id, day)
    for field in ("weight_kg", "body_fat_pct", "chest_cm", "waist_cm", "hips_cm", "arms_cm", "thighs_cm", "notes"):
        value = getattr(data, field)
        if value is not None:
            setattr(measurement, field, value)
    await db.flush()
    return measurement


async def get_summary(db: AsyncSession, user_id: uuid.UUID, date_from: date_ | None, date_to: date_ | None) -> ProgressSummaryOut:
    date_to = date_to or date_.today()
    date_from = date_from or (date_to - timedelta(days=DEFAULT_SUMMARY_WINDOW_DAYS))

    weight_result = await db.execute(
        select(BodyMeasurement)
        .where(
            BodyMeasurement.user_id == user_id,
            BodyMeasurement.date >= date_from,
            BodyMeasurement.date <= date_to,
            BodyMeasurement.weight_kg.is_not(None),
        )
        .order_by(BodyMeasurement.date)
    )
    weight_trend = list(weight_result.scalars().all())

    sessions_result = await db.execute(
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == SessionStatus.COMPLETED,
            WorkoutSession.finished_at.is_not(None),
        )
        .order_by(WorkoutSession.finished_at)
    )
    sessions = [
        s for s in sessions_result.scalars().all() if date_from <= s.finished_at.date() <= date_to
    ]

    return ProgressSummaryOut(
        weight_trend=weight_trend,
        workout_count=len(sessions),
        total_volume_kg=sum(s.total_volume_kg or 0 for s in sessions),
        volume_trend=[
            {"date": s.finished_at.date(), "total_volume_kg": s.total_volume_kg, "estimated_calories": s.estimated_calories}
            for s in sessions
        ],
    )
