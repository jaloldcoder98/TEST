from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services import auth_service
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TelegramAuthRequest, TokenResponse

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.register(db, data)


@router.post("/telegram", response_model=TokenResponse)
async def telegram_auth(data: TelegramAuthRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.telegram_auth(db, data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.login(db, data.username, data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.refresh(db, data.refresh_token)


@router.post("/logout")
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> dict:
    await auth_service.logout(db, data.refresh_token)
    return {"success": True}
