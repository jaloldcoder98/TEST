"""Promotes the Telegram ids in `BOOTSTRAP_ADMIN_TELEGRAM_IDS` to super_admin at startup
(docs/DECISIONS.md D-32).

Two rules make this safe to run on every boot:

* **Promote only, never demote.** An id that disappears from the variable keeps whatever role it
  has. Demotion is an administrative act with an audit trail, not a side effect of editing an
  environment file — and a typo there must never be able to lock everyone out.
* **Idempotent.** Running it a hundred times changes nothing after the first, so it can live in
  the startup path without guards.

An id that has never opened the bot has no account yet, so there is nothing to promote; it is
recorded and skipped, and the next boot after they sign in picks them up.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, TelegramUser, User
from app.models.enums import UserRole

logger = logging.getLogger(__name__)


async def promote_bootstrap_admins(db: AsyncSession, telegram_ids: list[int]) -> dict[str, list[int]]:
    """Returns what happened, split into promoted / already-admin / no-account-yet."""
    outcome: dict[str, list[int]] = {"promoted": [], "already": [], "no_account": []}
    if not telegram_ids:
        return outcome

    rows = (
        await db.execute(
            select(TelegramUser.telegram_id, User)
            .join(User, User.id == TelegramUser.user_id)
            .where(TelegramUser.telegram_id.in_(telegram_ids))
        )
    ).all()
    found = {telegram_id: user for telegram_id, user in rows}

    for telegram_id in telegram_ids:
        user = found.get(telegram_id)
        if user is None:
            outcome["no_account"].append(telegram_id)
            continue
        if user.role is UserRole.SUPER_ADMIN:
            outcome["already"].append(telegram_id)
            continue

        previous = user.role
        user.role = UserRole.SUPER_ADMIN
        db.add(
            AuditLog(
                user_id=user.id,
                action="role.bootstrap_promote",
                entity_type="user",
                entity_id=user.id,
                log_metadata={
                    "before": {"role": previous.value},
                    "after": {"role": UserRole.SUPER_ADMIN.value},
                    "reason": "BOOTSTRAP_ADMIN_TELEGRAM_IDS",
                },
            )
        )
        outcome["promoted"].append(telegram_id)

    await db.flush()
    return outcome


async def run_bootstrap(session_factory, telegram_ids: list[int]) -> None:
    """Startup hook. Never fatal: a database that is not ready yet is a reason to log and carry
    on, not to refuse to serve."""
    if not telegram_ids:
        return
    try:
        async with session_factory() as db:
            outcome = await promote_bootstrap_admins(db, telegram_ids)
            await db.commit()
        logger.info(
            "Bootstrap admins — promoted: %s, already super_admin: %s, no account yet: %s",
            outcome["promoted"], outcome["already"], outcome["no_account"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bootstrap admin promotion skipped: %s", exc)
