from datetime import date as date_

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.progress import BodyMeasurementOut, MeasurementLogRequest, ProgressSummaryOut, WeightLogRequest
from app.services import progress_service

router = APIRouter()


@router.get("", response_model=ProgressSummaryOut)
async def get_progress(
    date_from: date_ | None = Query(default=None, alias="from"),
    date_to: date_ | None = Query(default=None, alias="to"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressSummaryOut:
    return await progress_service.get_summary(db, user.id, date_from, date_to)


@router.post("/weight", response_model=BodyMeasurementOut)
async def log_weight(
    data: WeightLogRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> BodyMeasurementOut:
    return await progress_service.log_weight(db, user.id, data)


@router.post("/measurements", response_model=BodyMeasurementOut)
async def log_measurements(
    data: MeasurementLogRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> BodyMeasurementOut:
    return await progress_service.log_measurements(db, user.id, data)
