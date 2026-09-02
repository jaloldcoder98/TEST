"""AI Coach menu button — Phase 7 hasn't been built yet (blocked on an OpenAI API key that
hasn't been provided). An honest placeholder, matching the web app's /ai-coach page, rather than
a fake chat reply (spec.md §61: no mock data in production paths)."""

from aiogram import F, Router
from aiogram.types import Message

from locales import all_translations, t
from services.session import get_language

router = Router(name="ai_coach")


@router.message(F.text.in_(all_translations("menu.ai_coach")))
async def ai_coach_menu(message: Message) -> None:
    lang = get_language(message.from_user.id)
    await message.answer(t("ai_coach.not_ready", lang))
