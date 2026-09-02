import uuid
from datetime import date

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import FoodSource, MealType


class FoodItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Local nutrition database — spec.md §19: 'do not rely exclusively on AI-generated
    nutritional values'. AI food analysis (Phase 7) looks values up here first."""

    __tablename__ = "food_items"

    name_en: Mapped[str] = mapped_column(String(200))
    name_ru: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name_uz: Mapped[str | None] = mapped_column(String(200), nullable=True)
    calories_per_100g: Mapped[float] = mapped_column(Float)
    protein_g_per_100g: Mapped[float] = mapped_column(Float)
    carbs_g_per_100g: Mapped[float] = mapped_column(Float)
    fat_g_per_100g: Mapped[float] = mapped_column(Float)
    fiber_g_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[FoodSource] = mapped_column(Enum(FoodSource, name="food_source"), default=FoodSource.MANUAL)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)


class FoodLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "food_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[MealType] = mapped_column(Enum(MealType, name="meal_type"))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_calories: Mapped[float] = mapped_column(Float, default=0)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    items: Mapped[list["FoodLogItem"]] = relationship(back_populates="food_log", cascade="all, delete-orphan")


class FoodLogItem(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "food_log_items"

    food_log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("food_logs.id", ondelete="CASCADE"))
    food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("food_items.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200))
    estimated_grams: Mapped[float] = mapped_column(Float)
    calories: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    food_log: Mapped["FoodLog"] = relationship(back_populates="items")


class NutritionDaily(Base, UUIDPrimaryKeyMixin):
    """Rolled-up per user per day — avoids re-summing food_logs on every dashboard load."""

    __tablename__ = "nutrition_daily"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_nutrition_daily_user_date"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date)
    total_calories: Mapped[float] = mapped_column(Float, default=0)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    remaining_calories: Mapped[float | None] = mapped_column(Float, nullable=True)
