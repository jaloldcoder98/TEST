"""/start onboarding (spec.md §30):

  /start -> pick language -> POST /auth/telegram (creates a bot-only account the first time,
            or logs back into the linked one) -> main menu

/link (handlers/link.py) is the separate flow for attaching an *existing* web account instead
of the auto-provisioned bot-only one.
"""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.language import LANGUAGE_KEYBOARD
from keyboards.main_menu import main_menu_keyboard
from locales import t
from services.session import ensure_session

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "🏋️ GYM AI Coach\n\nO'zbekcha / Русский / English — choose your language:",
        reply_markup=LANGUAGE_KEYBOARD,
    )


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def on_language_selected(callback: CallbackQuery) -> None:
    lang = callback.data.split(":", 1)[1]
    user = callback.from_user

    try:
        session = await ensure_session(user.id, callback.message.chat.id, user.username, user.first_name, lang)
    except Exception:
        # Never swallow this silently — a user-facing "something went wrong" with no trace
        # anywhere makes real bugs (like a backend 500) invisible until someone thinks to check
        # the backend's own logs. Logging here means `docker compose logs telegram-bot` alone is
        # enough to diagnose an onboarding failure.
        logger.exception("Failed to establish session for telegram_id=%s during /start", user.id)
        await callback.message.answer(t("common.error", lang))
        await callback.answer()
        return

    # A returning, already-linked user keeps their previously-chosen language rather than
    # switching languages just because they tapped a different button on this /start — but for a
    # brand-new account, `session.language` *is* what was just picked, so this is a no-op there.
    name = user.first_name or user.username or ""
    await callback.message.answer(t("welcome_back", session.language, name=name), reply_markup=main_menu_keyboard(session.language))
    await callback.answer()
