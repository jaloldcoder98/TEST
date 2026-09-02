"""Progress: workout/volume summary (menu button) and /logweight, matching the web app's
/progress page's weight-logging (body measurements stay web-only for now — a lot of fields to
walk through by text; a reasonable Phase 6+ follow-up)."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from locales import all_translations, t
from services.api_client import BackendAPIError, backend
from services.session import call_authed, get_language
from states import LogWeight

router = Router(name="progress")


@router.message(F.text.in_(all_translations("menu.progress")))
async def progress_menu(message: Message) -> None:
    lang = get_language(message.from_user.id)
    user = message.from_user
    try:
        summary = await call_authed(
            user.id, message.chat.id, user.username, user.first_name, lang, backend.progress_summary
        )
    except BackendAPIError:
        await message.answer(t("common.error", lang))
        return

    text = t("progress.title", lang, count=summary["workout_count"], volume=summary["total_volume_kg"])
    text += "\n\n" + t("progress.log_weight_prompt", lang)
    await message.answer(text)


@router.message(Command("logweight"))
async def start_log_weight(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await state.set_state(LogWeight.weight)
    await message.answer(t("progress.ask_weight", lang))


@router.message(StateFilter(LogWeight.weight))
async def receive_weight(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    try:
        weight = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer(t("invalid_number", lang))
        return
    await state.clear()

    user = message.from_user
    try:
        await call_authed(
            user.id, message.chat.id, user.username, user.first_name, lang, lambda token: backend.log_weight(token, weight)
        )
    except BackendAPIError:
        await message.answer(t("common.error", lang))
        return

    await message.answer(t("progress.logged", lang, weight=weight))
