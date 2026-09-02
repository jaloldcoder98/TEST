import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import settings
from handlers import start

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(start.router)

    logging.info("GYM bot starting (long polling)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
