"""Async SQLAlchemy engine/session setup, shared by the API and by ARQ workers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# NullPool: a connection is opened per checkout and closed on release, never reused across
# asyncio event loops. Without this, anything that can run requests on more than one loop
# within the same process — a sync TestClient's per-call portal, pytest-asyncio's own loop,
# ARQ vs. the API — hits asyncpg's "Future attached to a different loop" errors the moment a
# pooled connection created on one loop is reused from another. The overhead of a fresh
# connection per request is negligible at this app's scale; revisit only if profiling in
# Phase 9 shows otherwise.
engine = create_async_engine(settings.database_url, echo=settings.debug, poolclass=NullPool)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in app.models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one session per request, committed/rolled back automatically."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
