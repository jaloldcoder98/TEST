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
from app.models import RefreshToken, User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse


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


async def logout(db: AsyncSession, refresh_token: str) -> None:
    token_hash = hash_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
