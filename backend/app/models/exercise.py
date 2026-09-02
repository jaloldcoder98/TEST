import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Language


class LookupMixin(UUIDPrimaryKeyMixin):
    """Shared shape for the four small reference tables (muscles, equipment, body_parts,
    categories) — plain lookup tables rather than hardcoded enums, so the admin panel (spec.md
    §38) can manage them without a migration."""

    slug: Mapped[str] = mapped_column(String(50), unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Muscle(Base, LookupMixin):
    __tablename__ = "muscles"


class Equipment(Base, LookupMixin):
    __tablename__ = "equipment"


class BodyPart(Base, LookupMixin):
    __tablename__ = "body_parts"


class Category(Base, LookupMixin):
    __tablename__ = "categories"


class Exercise(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "exercises"

    # e.g. "biceps/barbell-curl" — the source dataset's natural key (docs/ARCHITECTURE.md §1.3).
    external_id: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True)

    muscle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("muscles.id"))
    body_part_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("body_parts.id"))
    equipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.id"))
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))

    # Muscle *slugs*, not FKs — matches the source data shape 1:1 and avoids a join table for a
    # field we only ever display, never filter/aggregate by (docs/DATABASE.md notes this as a
    # deliberate simplification, revisit if that changes).
    secondary_muscles: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list)

    gif_url: Mapped[str] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Provenance — required so licensing status is always traceable (docs/ARCHITECTURE.md §1.6).
    source: Mapped[str] = mapped_column(String(50))
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    muscle: Mapped["Muscle"] = relationship()
    body_part: Mapped["BodyPart"] = relationship()
    equipment: Mapped["Equipment"] = relationship()
    category: Mapped["Category"] = relationship()
    translations: Mapped[list["ExerciseTranslation"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )


class ExerciseTranslation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One row per (exercise, language). Only `language=en` is populated by the importer — ru/uz
    are added later through the admin enrichment workflow (docs/ARCHITECTURE.md §5); never
    auto-generated during import (spec.md §6)."""

    __tablename__ = "exercise_translations"
    __table_args__ = (UniqueConstraint("exercise_id", "language", name="uq_exercise_translation_lang"),)

    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"))
    language: Mapped[Language] = mapped_column(Enum(Language, name="language"))
    name: Mapped[str] = mapped_column(String(200))
    instructions: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_machine_translated: Mapped[bool] = mapped_column(Boolean, default=False)

    exercise: Mapped["Exercise"] = relationship(back_populates="translations")
