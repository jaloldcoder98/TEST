"""Bootstrap admin promotion (docs/DECISIONS.md D-32).

Two properties carry the safety of running this on every boot: it only ever promotes, and it is
idempotent. Both are asserted, because either one silently breaking would be discovered as
"everyone lost admin after a deploy" or "a stale env var quietly demoted someone".
"""

import contextlib

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.bootstrap import promote_bootstrap_admins
from app.core.config import get_settings
from app.models import TelegramUser, User
from app.models.enums import UserRole
from tests.conftest import BOT_HEADERS, new_telegram_id

pytestmark = pytest.mark.asyncio


@contextlib.asynccontextmanager
async def session():
    """A session on an engine created inside *this* test's event loop.

    The application's shared engine pools its connections on whichever loop first touched it —
    the session-scoped TestClient's — so reusing it from an independently-run async test raises
    "attached to a different loop". A short-lived engine per test avoids the problem entirely.
    """
    engine = create_async_engine(get_settings().database_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            yield db
    finally:
        await engine.dispose()


async def _role_of(telegram_id: int) -> UserRole:
    async with session() as db:
        user = (
            await db.execute(
                select(User).join(TelegramUser, TelegramUser.user_id == User.id).where(
                    TelegramUser.telegram_id == telegram_id
                )
            )
        ).scalar_one()
        return user.role


def _create_account(client, telegram_id: int) -> None:
    response = client.post(
        "/api/v1/auth/telegram", json={"telegram_id": telegram_id, "chat_id": telegram_id}, headers=BOT_HEADERS
    )
    assert response.status_code == 200, response.text


async def test_promotes_an_existing_account_to_super_admin(client) -> None:
    telegram_id = new_telegram_id()
    _create_account(client, telegram_id)
    assert await _role_of(telegram_id) is UserRole.USER

    async with session() as db:
        outcome = await promote_bootstrap_admins(db, [telegram_id])
        await db.commit()

    assert outcome["promoted"] == [telegram_id]
    assert await _role_of(telegram_id) is UserRole.SUPER_ADMIN


async def test_is_idempotent(client) -> None:
    telegram_id = new_telegram_id()
    _create_account(client, telegram_id)

    async with session() as db:
        await promote_bootstrap_admins(db, [telegram_id])
        await db.commit()
    async with session() as db:
        second = await promote_bootstrap_admins(db, [telegram_id])
        await db.commit()

    assert second["promoted"] == []
    assert second["already"] == [telegram_id]
    assert await _role_of(telegram_id) is UserRole.SUPER_ADMIN


async def test_never_demotes_an_id_that_left_the_list(client) -> None:
    """Removing an id from the environment variable must not take their role away: demotion is
    an audited administrative act, not a side effect of editing a config file."""
    telegram_id = new_telegram_id()
    _create_account(client, telegram_id)

    async with session() as db:
        await promote_bootstrap_admins(db, [telegram_id])
        await db.commit()

    async with session() as db:
        await promote_bootstrap_admins(db, [])  # id no longer listed
        await db.commit()

    assert await _role_of(telegram_id) is UserRole.SUPER_ADMIN


async def test_unknown_telegram_id_is_recorded_not_fatal(client) -> None:
    """Someone listed who has never opened the bot has no account to promote yet. That is a
    normal first-deploy state, so it is reported and skipped rather than raising."""
    async with session() as db:
        outcome = await promote_bootstrap_admins(db, [new_telegram_id()])
        await db.commit()

    assert outcome["promoted"] == [] and len(outcome["no_account"]) == 1


async def test_promotion_is_written_to_the_audit_log(client) -> None:
    """Invariant 6 — a role change is exactly the kind of act that must leave a trace."""
    from app.models import AuditLog

    telegram_id = new_telegram_id()
    _create_account(client, telegram_id)

    async with session() as db:
        await promote_bootstrap_admins(db, [telegram_id])
        await db.commit()

    async with session() as db:
        entry = (
            await db.execute(select(AuditLog).where(AuditLog.action == "role.bootstrap_promote"))
        ).scalars().all()
    assert entry, "bootstrap promotion left no audit trail"
    assert entry[-1].log_metadata["after"]["role"] == "super_admin"
