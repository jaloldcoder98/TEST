import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from config import settings
from handlers import ai_coach, common, exercises, help as help_handler, link, nutrition, profile, progress, start, workouts
from services.api_client import backend

logging.basicConfig(level=logging.INFO)

BOT_COMMANDS = [
    BotCommand(command="start", description="Restart / main menu"),
    BotCommand(command="link", description="Link an existing web account"),
    BotCommand(command="newworkout", description="Create a workout"),
    BotCommand(command="done", description="Finish adding exercises to a new workout"),
    BotCommand(command="logmeal", description="Log a meal"),
    BotCommand(command="logweight", description="Log today's weight"),
    BotCommand(command="cancel", description="Cancel the current action"),
    BotCommand(command="help", description="Show available commands"),
]


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Order matters where callback_data/state filters could otherwise be ambiguous (e.g. two
    # routers both matching a "lang:" prefix) — see the comment in handlers/profile.py, which
    # sidesteps that by using a distinct "setlang:" prefix instead of relying on router order.
    for router in (start.router, link.router, common.router, workouts.router, exercises.router, nutrition.router, progress.router, profile.router, ai_coach.router, help_handler.router):
        dp.include_router(router)

    await bot.set_my_commands(BOT_COMMANDS)

    # The persistent button next to the message box (an alternative entry point to the /start
    # message's own button — this one's always there, even before a user has ever typed
    # anything). Same https:// requirement and same graceful fallback as handlers/start.py.
    if settings.frontend_url.startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Open App", web_app=WebAppInfo(url=settings.frontend_url))
        )
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    logging.info("GYM bot starting (long polling)...")
    try:
        await dp.start_polling(bot)
    finally:
        await backend.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
