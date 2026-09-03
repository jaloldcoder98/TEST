"""/start onboarding.

Primary flow (when FRONTEND_URL is configured, config.py): /start sends a single "Open App"
button that launches the frontend as a Telegram Mini App (Web App). Everything after that —
picking a language, creating workouts, nutrition, AI coach, progress — happens inside that web
page: it silently authenticates itself via `Telegram.WebApp.initData`
(frontend/components/telegram/telegram-webapp-gate.tsx + POST /auth/telegram-webapp), so there's
no separate language-picker step here and no bot-side account bootstrapping to do.

Fallback flow (FRONTEND_URL not set — e.g. no public HTTPS URL configured yet): the classic
text/button flow this bot shipped with originally — pick a language, POST /auth/telegram, main
menu — stays available so the bot is never broken while a Mini App URL isn't ready. All the other
handlers/*.py commands (newworkout, logmeal, etc.) keep working either way; the Mini App is the
front door, not a replacement for what those already do.

/link (handlers/link.py) is the separate flow for attaching an *existing* web account instead
of the auto-provisioned bot-only one.
"""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from config import settings
from keyboards.language import LANGUAGE_KEYBOARD
from keyboards.main_menu import main_menu_keyboard
from locales import t
from services.session import ensure_session

logger = logging.getLogger(__name__)

router = Router(name="start")


def _open_app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏋️ Ilovani ochish / Open App", web_app=WebAppInfo(url=settings.frontend_url))]]
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    # Telegram rejects a web_app button whose url isn't https:// outright (it would fail the
    # sendMessage call itself, surfacing as a confusing bot-side error) — so an http:// or unset
    # FRONTEND_URL falls back to the text flow rather than attempting a button Telegram won't
    # accept.
    if settings.frontend_url.startswith("https://"):
        await message.answer(
            "🏋️ GYM AI Coach\n\n"
            "Barcha imkoniyatlar — mashqlar, ovqatlanish, AI Coach, progress — ilova ichida.\n"
            "All features — workouts, nutrition, AI Coach, progress — live inside the app.\n\n"
            "Quyidagi tugmani bosing / Tap the button below:",
            reply_markup=_open_app_keyboard(),
        )
        return

    # No public Mini App URL configured yet — fall back to the original text-flow onboarding.
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
