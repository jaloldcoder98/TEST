import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, UnauthorizedError
from app.core.security import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import RefreshToken, TelegramUser, User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TelegramAuthRequest, TokenResponse


async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh_token), expires_at=expires_at))
    await db.flush()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def register(db: AsyncSession, data: RegisterRequest) -> TokenResponse:
    repo = UserRepository(db)

    if await repo.get_by_username(data.username) is not None:
        raise AppError("USERNAME_TAKEN", "This username is already taken", 409)
    if data.email and await repo.get_by_email(data.email) is not None:
        raise AppError("EMAIL_TAKEN", "This email is already registered", 409)

    user = await repo.create(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        language=data.language,
    )
    return await _issue_tokens(db, user)


async def login(db: AsyncSession, username: str, password: str) -> TokenResponse:
    repo = UserRepository(db)
    user = await repo.get_by_username(username)
    if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid username or password")
    if not user.is_active:
        raise UnauthorizedError("Account is deactivated")
    return await _issue_tokens(db, user)


async def telegram_auth(db: AsyncSession, data: TelegramAuthRequest) -> TokenResponse:
    existing = (
        await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == data.telegram_id))
    ).scalar_one_or_none()

    if existing is not None:
        existing.chat_id = data.chat_id
        if data.telegram_username:
            existing.telegram_username = data.telegram_username
        repo = UserRepository(db)
        user = await repo.get_by_id(existing.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Account is deactivated")
        await db.flush()
        return await _issue_tokens(db, user)

    # No link yet — auto-provision a bot-only account (password_hash stays null; spec.md's
    # users.password_hash is nullable precisely for this case) rather than forcing a Telegram
    # user through a web-style registration flow they can't fill out inline.
    repo = UserRepository(db)
    username = f"tg_{data.telegram_id}"
    suffix = 0
    while await repo.get_by_username(username) is not None:
        suffix += 1
        username = f"tg_{data.telegram_id}_{suffix}"

    user = await repo.create(
        username=username,
        email=None,
        password_hash=None,
        first_name=data.first_name,
        last_name=None,
        language=data.language,
    )
    db.add(
        TelegramUser(
            user_id=user.id,
            telegram_id=data.telegram_id,
            chat_id=data.chat_id,
            telegram_username=data.telegram_username,
            linked_at=datetime.now(timezone.utc),
        )
    )
    await db.flush()
    return await _issue_tokens(db, user)


async def refresh(db: AsyncSession, refresh_token: str) -> TokenResponse:
    try:
        payload = decode_refresh_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Not a refresh token")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError) as exc:
        raise UnauthorizedError("Invalid or expired refresh token") from exc

    token_hash = hash_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is None or stored.revoked_at is not None or stored.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError("Refresh token is no longer valid")

    # Rotate: revoke the used token and issue a fresh pair (spec.md §37 — never reuse a refresh token).
    stored.revoked_at = datetime.now(timezone.utc)

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return await _issue_tokens(db, user)


async def link_telegram(db: AsyncSession, user_id: uuid.UUID, telegram_id: int, chat_id: int, telegram_username: str | None) -> None:
    """Attach a Telegram account to an *already-authenticated* user — the bot calls this after
    validating the person's username/password via POST /auth/login, for someone who registered
    on the web and wants the bot to use that same account instead of auto-provisioning a new
    tg_<id> one."""
    existing = (
        await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if existing is not None and existing.user_id != user_id:
        raise AppError("TELEGRAM_ALREADY_LINKED", "This Telegram account is already linked to another user", 409)

    if existing is not None:
        existing.chat_id = chat_id
        existing.telegram_username = telegram_username
    else:
        db.add(
            TelegramUser(
                user_id=user_id, telegram_id=telegram_id, chat_id=chat_id,
                telegram_username=telegram_username, linked_at=datetime.now(timezone.utc),
            )
        )
    await db.flush()


async def logout(db: AsyncSession, refresh_token: str) -> None:
    token_hash = hash_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
