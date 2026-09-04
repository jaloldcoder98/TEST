import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import TelegramUser, User, UserProfile


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.db.execute(
            select(User)
            .join(TelegramUser, TelegramUser.user_id == User.id)
            .options(selectinload(User.profile))
            .where(TelegramUser.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self.db.add(user)
        await self.db.flush()
        self.db.add(UserProfile(user_id=user.id))
        await self.db.flush()
        return user
