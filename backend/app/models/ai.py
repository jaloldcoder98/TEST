import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConversationContext, MessageRole


class AIConversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    context_type: Mapped[ConversationContext] = mapped_column(Enum(ConversationContext, name="conversation_context"))
    # Rolling summary of older turns (spec.md §33), so only this + the last N ai_messages are
    # sent to the model — raw history stays intact in ai_messages for audit.
    summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    messages: Mapped[list["AIMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class AIMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(String)
    # e.g. a generated workout card (spec.md §15) — always Pydantic-validated before being
    # written here (see app/ai/schemas), never raw model output.
    structured_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    conversation: Mapped["AIConversation"] = relationship(back_populates="messages")
