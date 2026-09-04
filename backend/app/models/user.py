import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ActivityLevel, ExperienceLevel, Gender, Goal, Language, UserRole


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    # Kept nullable and unused: Telegram is the only identity (D-10), so nothing writes this
    # today. It stays for a future notification/receipt address rather than being dropped and
    # re-added later.
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[Language] = mapped_column(Enum(Language, name="language"), default=Language.UZ)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.USER)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    telegram_account: Mapped["TelegramUser"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender, name="gender"), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    goal: Mapped[Goal | None] = mapped_column(Enum(Goal, name="goal"), nullable=True)
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(
        Enum(ExperienceLevel, name="experience_level"), nullable=True
    )
    activity_level: Mapped[ActivityLevel | None] = mapped_column(
        Enum(ActivityLevel, name="activity_level"), nullable=True
    )
    daily_calorie_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein_target_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carbs_target_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fat_target_g: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")


class TelegramUser(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "telegram_users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    # Plain `Mapped[int]` maps to a 32-bit INTEGER, but Telegram user/chat ids routinely exceed
    # that (e.g. 7741611853) since Telegram widened its id space — BigInteger avoids
    # "value out of int32 range" errors on real accounts.
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="telegram_account")


class RefreshToken(Base, UUIDPrimaryKeyMixin):
    """One row per issued refresh token, stored as a SHA-256 hash so a database dump yields
    nothing replayable.

    Tokens issued from one another form a *family* (D-14): logging in starts a family, and every
    rotation adds a link to the same chain. That is what makes reuse detection possible — if a
    token that has already been rotated away is presented again, the only explanations are a
    stolen copy or a client bug, and in either case the safe move is to revoke the whole family
    rather than the single token, since the thief and the victim now hold siblings of it.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Shared by every token descended from one login, so a breach revokes the chain, not a link.
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    # Set when this token is rotated: its presence is exactly what marks a token as "already
    # used", which is the signal reuse detection keys off.
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Why it was revoked — "rotated", "logout", "reuse_detected", "account_deactivated". Kept
    # because "the whole family died at 03:14" is only useful if you can tell which of those it was.
    revoked_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Favorite(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    favoritable_type: Mapped[str] = mapped_column(String(20))  # exercise|workout|food_item
    favoritable_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Never logs passwords, tokens, or images (spec.md §44) — only structured, non-sensitive
    metadata about what action happened."""

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    log_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
