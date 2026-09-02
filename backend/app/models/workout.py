import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RecordType, SessionStatus, WorkoutCategory
from app.models.exercise import Exercise  # noqa: F401 — needed for the relationship() below


class WorkoutTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workout_templates"

    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[WorkoutCategory] = mapped_column(Enum(WorkoutCategory, name="workout_category"))
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Workout(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workouts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_templates.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    day: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. "monday"
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", order_by="WorkoutExercise.order"
    )


class WorkoutExercise(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "workout_exercises"

    workout_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workouts.id", ondelete="CASCADE"))
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercises.id"))
    order: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    workout: Mapped["Workout"] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship()


class WorkoutSession(Base, UUIDPrimaryKeyMixin):
    """A single instance of *doing* a workout. Sets are logged against the session (not the
    static WorkoutExercise) so history stays immutable even if the workout template changes
    later (docs/DATABASE.md)."""

    __tablename__ = "workout_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workout_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workouts.id"))
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus, name="session_status"), default=SessionStatus.IN_PROGRESS)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    total_volume_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)

    sets: Mapped[list["WorkoutSet"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class WorkoutSet(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "workout_sets"

    workout_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_sessions.id", ondelete="CASCADE"), index=True
    )
    workout_exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_exercises.id"))
    set_number: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # timed exercises
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    session: Mapped["WorkoutSession"] = relationship(back_populates="sets")


class PersonalRecord(Base, UUIDPrimaryKeyMixin):
    """Materialized on set completion (Phase 4 service logic), not recomputed on every read."""

    __tablename__ = "personal_records"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercises.id"))
    record_type: Mapped[RecordType] = mapped_column(Enum(RecordType, name="record_type"))
    value: Mapped[float] = mapped_column(Float)
    achieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    workout_set_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_sets.id"))
