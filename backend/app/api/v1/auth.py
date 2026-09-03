from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.rate_limit import rate_limit
from app.services import auth_service
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TelegramAuthRequest, TokenResponse

router = APIRouter()

# Limits are per client IP (app/core/rate_limit.py). Login/register are the classic
# brute-force/credential-stuffing targets so they're the tightest; refresh and the Telegram
# auto-auth endpoint get more headroom since a legitimate client can hit them fairly often
# (token rotation, bot reconnects) without that being suspicious.
_LOGIN_LIMIT = Depends(rate_limit("login", max_requests=10, window_seconds=60))
_REGISTER_LIMIT = Depends(rate_limit("register", max_requests=10, window_seconds=60))
_REFRESH_LIMIT = Depends(rate_limit("refresh", max_requests=30, window_seconds=60))
_TELEGRAM_AUTH_LIMIT = Depends(rate_limit("telegram_auth", max_requests=30, window_seconds=60))


@router.post("/register", response_model=TokenResponse, dependencies=[_REGISTER_LIMIT])
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.register(db, data)


@router.post("/telegram", response_model=TokenResponse, dependencies=[_TELEGRAM_AUTH_LIMIT])
async def telegram_auth(data: TelegramAuthRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.telegram_auth(db, data)


@router.post("/login", response_model=TokenResponse, dependencies=[_LOGIN_LIMIT])
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.login(db, data.username, data.password)


@router.post("/refresh", response_model=TokenResponse, dependencies=[_REFRESH_LIMIT])
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.refresh(db, data.refresh_token)


@router.post("/logout")
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> dict:
    await auth_service.logout(db, data.refresh_token)
    return {"success": True}
