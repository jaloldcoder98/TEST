# TODO(webapp-first): TZ §2/§45 — meal-logging FSM duplicates the Web App's nutrition diary; same treatment as
# handlers/workouts.py (stub + legacy flag, audit §2).
#
# TZ §18 — a photo sent to the bot should not be analyzed in chat. Reply with
# "Food analysis is available in GYM App" plus a web_app button at ?startapp=nutrition-analyze,
# and let the Web App's camera/upload flow do the work.
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

"""Nutrition: today's totals (menu button) and manual meal logging via /logmeal — mirrors the
web app's /nutrition page (manual entry only; AI photo analysis is still Phase 7)."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.nutrition import meal_type_keyboard
from locales import all_translations, t
from services.api_client import BackendAPIError, backend
from services.session import call_authed, get_language
from states import LogFood

router = Router(name="nutrition")


@router.message(F.text.in_(all_translations("menu.nutrition")))
async def nutrition_menu(message: Message) -> None:
    lang = get_language(message.from_user.id)
    user = message.from_user
    try:
        daily = await call_authed(
            user.id, message.chat.id, user.username, user.first_name, lang, backend.today_nutrition
        )
    except BackendAPIError:
        await message.answer(t("common.error", lang))
        return

    text = t("nutrition.today_title", lang, calories=round(daily["total_calories"]))
    if daily["calorie_target"] is not None:
        text += "\n" + t(
            "nutrition.today_remaining", lang, remaining=round(daily["remaining_calories"]), target=daily["calorie_target"]
        )
    else:
        text += "\n" + t("nutrition.today_no_target", lang)
    if not daily["logs"]:
        text += "\n\n" + t("nutrition.today_empty", lang)
    text += "\n\n" + t("nutrition.log_prompt", lang)
    await message.answer(text)


@router.message(Command("logmeal"))
async def start_log_meal(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await message.answer(t("nutrition.meal_type_prompt", lang), reply_markup=meal_type_keyboard(lang))


@router.callback_query(lambda c: c.data and c.data.startswith("meal:"))
async def on_meal_type_selected(callback: CallbackQuery, state: FSMContext) -> None:
    lang = get_language(callback.from_user.id)
    meal_type = callback.data.split(":", 1)[1]
    await state.update_data(meal_type=meal_type)
    await state.set_state(LogFood.name)
    await callback.message.answer(t("nutrition.ask_name", lang))
    await callback.answer()


@router.message(StateFilter(LogFood.name))
async def receive_food_name(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await state.update_data(name=message.text.strip())
    await state.set_state(LogFood.grams)
    await message.answer(t("nutrition.ask_grams", lang))


async def _ask_number(message: Message, state: FSMContext, field: str, next_state, next_prompt_key: str) -> bool:
    """Parses message.text as a float, stores it under `field`, and advances the FSM — returns
    False (without advancing) if it wasn't a valid number, so the caller can just `return`."""
    lang = get_language(message.from_user.id)
    try:
        value = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer(t("invalid_number", lang))
        return False
    await state.update_data(**{field: value})
    if next_state is not None:
        await state.set_state(next_state)
        await message.answer(t(next_prompt_key, lang))
    return True


@router.message(StateFilter(LogFood.grams))
async def receive_grams(message: Message, state: FSMContext) -> None:
    await _ask_number(message, state, "estimated_grams", LogFood.calories, "nutrition.ask_calories")


@router.message(StateFilter(LogFood.calories))
async def receive_calories(message: Message, state: FSMContext) -> None:
    await _ask_number(message, state, "calories", LogFood.protein, "nutrition.ask_protein")


@router.message(StateFilter(LogFood.protein))
async def receive_protein(message: Message, state: FSMContext) -> None:
    await _ask_number(message, state, "protein_g", LogFood.carbs, "nutrition.ask_carbs")


@router.message(StateFilter(LogFood.carbs))
async def receive_carbs(message: Message, state: FSMContext) -> None:
    await _ask_number(message, state, "carbs_g", LogFood.fat, "nutrition.ask_fat")


@router.message(StateFilter(LogFood.fat))
async def receive_fat_and_submit(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    ok = await _ask_number(message, state, "fat_g", None, "")
    if not ok:
        return

    data = await state.get_data()
    await state.clear()
    payload = {
        "meal_type": data["meal_type"],
        "items": [
            {
                "name": data["name"],
                "estimated_grams": data["estimated_grams"],
                "calories": data["calories"],
                "protein_g": data["protein_g"],
                "carbs_g": data["carbs_g"],
                "fat_g": data["fat_g"],
            }
        ],
    }

    user = message.from_user
    try:
        await call_authed(
            user.id, message.chat.id, user.username, user.first_name, lang, lambda token: backend.log_food(token, payload)
        )
    except BackendAPIError:
        await message.answer(t("common.error", lang))
        return

    await message.answer(t("nutrition.logged", lang, name=data["name"], calories=round(data["calories"])))
