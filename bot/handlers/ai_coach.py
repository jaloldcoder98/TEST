# TODO(webapp-first): TZ §2/§45 — duplicates the Web App's ai screen. Reduce to an "Open in GYM App" reply
# with a web_app button at ?startapp=ai (audit §2, legacy flag applies here too).
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

"""AI Coach: a real chat against POST /ai/chat (Phase 7). Every reply goes through the same
backend endpoint the web app uses, so an unconfigured AI provider produces the exact same honest
"not connected yet" message everywhere (spec.md §61: no mock data in production paths) rather
than a bot-only hardcoded placeholder.

/cancel while chatting is handled by handlers/common.py — that router is registered before this
one in main.py and its Command("cancel") filter isn't state-scoped, so it always intercepts
/cancel first and clears the FSM state (including AICoach.chatting) before this router ever sees
the update.
"""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from locales import all_translations, t
from services.api_client import BackendAPIError, backend
from services.session import call_authed, get_language
from states import AICoach

router = Router(name="ai_coach")


@router.message(F.text.in_(all_translations("menu.ai_coach")))
async def ai_coach_menu(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await state.set_state(AICoach.chatting)
    await state.update_data(conversation_id=None)
    await message.answer(t("ai_coach.prompt", lang))


@router.message(StateFilter(AICoach.chatting))
async def ai_coach_message(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    text = (message.text or "").strip()
    if not text:
        return

    data = await state.get_data()
    conversation_id = data.get("conversation_id")
    user = message.from_user

    try:
        response = await call_authed(
            user.id,
            message.chat.id,
            user.username,
            user.first_name,
            lang,
            lambda token: backend.ai_chat(token, text, conversation_id),
        )
    except BackendAPIError as exc:
        if exc.code == "AI_NOT_CONFIGURED":
            await message.answer(t("ai_coach.not_ready", lang))
            await state.clear()
            return
        await message.answer(t("common.error", lang))
        return

    await state.update_data(conversation_id=response["conversation_id"])
    await message.answer(response["message"])
