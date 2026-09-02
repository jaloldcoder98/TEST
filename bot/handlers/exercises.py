"""Exercise search — a lightweight, text-based version of the web app's /exercises page. Full
filtering by muscle/equipment/body-part/category lives on the web; the bot covers the common
"what's a good exercise for X" case via free-text search against the same /exercises endpoint."""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from locales import all_translations, t
from services.api_client import BackendAPIError, backend
from services.session import get_language
from states import ExerciseSearch

router = Router(name="exercises")

RESULT_LIMIT = 8


@router.message(F.text.in_(all_translations("menu.exercises")))
async def exercises_menu(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await state.set_state(ExerciseSearch.query)
    await message.answer(t("exercises.search_prompt", lang))


@router.message(StateFilter(ExerciseSearch.query))
async def run_search(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    query = message.text.strip()
    await state.clear()

    try:
        result = await backend.list_exercises(None, q=query, lang=lang, pageSize=RESULT_LIMIT)
    except BackendAPIError:
        await message.answer(t("common.error", lang))
        return

    items = result["items"]
    if not items:
        await message.answer(t("exercises.no_results", lang, query=query))
        return

    lines = [t("exercises.result_line", lang, name=ex["name"], muscle=ex["muscle"]) for ex in items]
    text = "\n".join(lines)
    if result["total"] > len(items):
        text += "\n\n" + t("exercises.more_hint", lang, count=len(items), total=result["total"])
    await message.answer(text)
