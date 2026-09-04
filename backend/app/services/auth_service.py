"""Session lifecycle: Telegram identity in, tokens out (docs/DECISIONS.md D-10 … D-20).

There is exactly one way to become authenticated here — a Telegram identity, arriving by one of
two doors that differ only in how they earn trust:

* `telegram_webapp_auth` — the Mini App posts the raw `initData` string it got from the Telegram
  client. Trusted because its HMAC signature is verified against the bot token, which client-side
  JavaScript does not have.
* `bot_telegram_auth` — the bot posts a `telegram_id` it read off a real Telegram update. There is
  no signature to check, so trust comes from the shared secret the route requires (D-20); without
  it, anyone able to reach the endpoint could name any `telegram_id`.

Both funnel into `_login_or_provision`, so a person gets the same account whichever door they
came through, and no second identity model exists to drift.

Passwords are gone (D-10): no register, no login, no password-based account linking.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, UnauthorizedError
from app.core.init_data_guard import record_and_check
from app.core.security import (
    JWTError,
    create_access_token,
    create_refresh_token,
    csrf_token_for,
    decode_refresh_token,
    hash_token,
    refresh_token_lifetime,
)
from app.core.telegram_webapp import verify_telegram_webapp_init_data
from app.models import RefreshToken, TelegramUser, User
from app.models.enums import Language, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TelegramAuthRequest

settings = get_settings()


@dataclass(frozen=True)
class AuthSession:
    """What a successful authentication produces.

    The refresh token is returned to the *caller of this service*, not necessarily to the browser:
    the web route puts it in an httpOnly cookie (D-13) and never lets it reach JavaScript, while
    the bot — which has no cookie jar — receives it in the response body.
    """

    user: User
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime
    csrf_token: str

    @property
    def refresh_max_age_seconds(self) -> int:
        remaining = self.refresh_expires_at - datetime.now(timezone.utc)
        return max(0, int(remaining.total_seconds()))


async def _issue_session(db: AsyncSession, user: User, family_id: uuid.UUID | None = None) -> AuthSession:
    """Mint a token pair. Passing `family_id` continues an existing chain (a rotation); omitting
    it starts a new one (a fresh login)."""
    family_id = family_id or uuid.uuid4()
    access_token = create_access_token(user.id, user.role)
    refresh_token, expires_at = create_refresh_token(user.id, family_id, user.role)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            family_id=family_id,
            expires_at=expires_at,
        )
    )
    await db.flush()
    return AuthSession(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
        refresh_expires_at=expires_at,
        csrf_token=csrf_token_for(refresh_token),
    )


async def revoke_family(db: AsyncSession, family_id: uuid.UUID, reason: str) -> int:
    """Revoke every live token descended from one login. Returns how many were affected."""
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc), revoked_reason=reason)
    )
    return result.rowcount or 0


async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID, reason: str) -> int:
    """Cut every session a user has. Used when an account is deactivated, banned or scheduled for
    deletion (D-142) — a 15-minute access token is the only access that survives, by design."""
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc), revoked_reason=reason)
    )
    return result.rowcount or 0


async def _login_or_provision(
    db: AsyncSession,
    *,
    telegram_id: int,
    chat_id: int,
    telegram_username: str | None,
    first_name: str | None,
    language: Language,
) -> AuthSession:
    """Log into the account linked to this `telegram_id`, or create one.

    Idempotent per `telegram_id`, which is what lets the Mini App and the bot be the same account
    without any linking step: whoever arrives first creates it, everyone after signs into it.
    """
    existing = (
        await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id))
    ).scalar_one_or_none()

    repo = UserRepository(db)

    if existing is not None:
        existing.chat_id = chat_id
        if telegram_username:
            existing.telegram_username = telegram_username
        user = await repo.get_by_id(existing.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Account is deactivated")
        await db.flush()
        return await _issue_session(db, user)

    username = f"tg_{telegram_id}"
    suffix = 0
    while await repo.get_by_username(username) is not None:
        suffix += 1
        username = f"tg_{telegram_id}_{suffix}"

    user = await repo.create(
        username=username,
        email=None,
        first_name=first_name,
        last_name=None,
        language=language,
    )
    db.add(
        TelegramUser(
            user_id=user.id,
            telegram_id=telegram_id,
            chat_id=chat_id,
            telegram_username=telegram_username,
            linked_at=datetime.now(timezone.utc),
        )
    )
    await db.flush()
    return await _issue_session(db, user)


async def bot_telegram_auth(db: AsyncSession, data: TelegramAuthRequest) -> AuthSession:
    return await _login_or_provision(
        db,
        telegram_id=data.telegram_id,
        chat_id=data.chat_id,
        telegram_username=data.telegram_username,
        first_name=data.first_name,
        language=data.language,
    )


async def telegram_webapp_auth(db: AsyncSession, init_data: str) -> AuthSession:
    if not settings.telegram_bot_tokens:
        raise AppError("TELEGRAM_NOT_CONFIGURED", "Telegram integration is not configured on this server", 503)

    parsed = verify_telegram_webapp_init_data(init_data, settings.telegram_bot_tokens)
    # Only after the signature checks out: counting unverified payloads would let anyone fill the
    # abuse counters with garbage. Note this throttles repetition, it is not a nonce (D-17).
    await record_and_check(init_data)

    tg_user = parsed.get("user") or {}
    telegram_id = tg_user.get("id")
    if telegram_id is None:
        raise UnauthorizedError("Telegram Web App init data is missing the user")

    language = Language.UZ
    raw_language = (tg_user.get("language_code") or "").lower()
    if raw_language.startswith("ru"):
        language = Language.RU
    elif raw_language.startswith("uz"):
        language = Language.UZ
    elif raw_language:
        language = Language.EN

    # A Mini App opened from a private chat carries no separate chat id the way a bot Update does
    # — but in a 1:1 chat Telegram's chat id *is* the user id, so this matches what the bot sends.
    return await _login_or_provision(
        db,
        telegram_id=telegram_id,
        chat_id=telegram_id,
        telegram_username=tg_user.get("username"),
        first_name=tg_user.get("first_name"),
        language=language,
    )


async def refresh(db: AsyncSession, refresh_token: str) -> AuthSession:
    """Rotate a refresh token, detecting reuse.

    A token that has already been rotated away must never work again. If one is presented, either
    it was stolen or a client is buggy; both are handled the same way, by revoking the entire
    family — the thief holds a sibling of this token, so killing only the presented one would
    leave them logged in.
    """
    try:
        payload = decode_refresh_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Not a refresh token")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError) as exc:
        raise UnauthorizedError("Invalid or expired refresh token") from exc

    stored = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)))
    ).scalar_one_or_none()

    if stored is None:
        raise UnauthorizedError("Refresh token is no longer valid")

    if stored.replaced_by_id is not None or stored.revoked_at is not None:
        await revoke_family(db, stored.family_id, "reuse_detected")
        # Committed here, not flushed. `get_db` rolls the session back on any exception, and the
        # next line raises one — so a flush would leave the revocation on the floor and the
        # response to a detected theft would be "401" with nothing actually revoked. Committing
        # first makes the rollback a no-op for work that must survive the error.
        await db.commit()
        raise UnauthorizedError("Refresh token was already used — all sessions have been revoked")

    if stored.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError("Refresh token has expired")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    session = await _issue_session(db, user, family_id=stored.family_id)

    issued = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(session.refresh_token))
        )
    ).scalar_one()
    stored.replaced_by_id = issued.id
    stored.revoked_at = datetime.now(timezone.utc)
    stored.revoked_reason = "rotated"
    await db.flush()
    return session


async def logout(db: AsyncSession, refresh_token: str) -> None:
    """Revoke the whole family, not just this token: "log me out" means the session, and a
    session is the chain. Unknown or malformed tokens are a no-op — logout should never be a way
    to learn whether a token was real."""
    try:
        stored = (
            await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)))
        ).scalar_one_or_none()
    except Exception:  # noqa: BLE001
        return
    if stored is not None:
        await revoke_family(db, stored.family_id, "logout")
        await db.flush()


def session_max_age_seconds(role: UserRole) -> int:
    return int(refresh_token_lifetime(role).total_seconds())
