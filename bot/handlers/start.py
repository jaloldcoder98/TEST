"""/start onboarding (spec.md §30):

  /start -> no linked account -> pick language -> (Phase 6: create account via backend)
         -> existing account -> show dashboard

Phase 2 wires the language-selection step end-to-end against a stub; Phase 6 replaces the stub
with real calls to POST /auth/register and GET /users/me on the backend.
"""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.language import LANGUAGE_KEYBOARD
from keyboards.main_menu import main_menu_keyboard
from locales import t

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
    # Phase 6: persist this on the user's backend profile (PATCH /users/me) once account
    # creation/linking is implemented; for now it only drives this session's replies.
    await callback.message.answer(t("welcome", lang), reply_markup=main_menu_keyboard(lang))
    await callback.answer()
