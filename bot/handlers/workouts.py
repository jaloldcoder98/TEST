# TODO(webapp-first): TZ §2/§45 — 299 lines of workout UI inside the chat: this is the single largest violation of
# "the bot must NOT duplicate Web App functionality". Everything here (create workout, pick
# exercises, log sets, history) already exists in the Web App.
#
# Plan (audit §2): replace the handlers with a one-line "Open in GYM App" reply carrying a
# web_app button at ?startapp=workouts, and move this file to bot/handlers/legacy/ behind an
# ENABLE_LEGACY_BOT_UI flag that defaults to off — so nothing breaks in a deployment that has
# no public HTTPS URL yet. Update bot/tests/test_workouts_handler.py to match.
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

"""Workouts: list/create/start/track, the bot's equivalent of the web app's /workouts pages.
Session tracking has no GET /workout-sessions/{id} to resume from (docs/API.md) — same
constraint the frontend documents — so all session state lives in the FSM context for the
duration of one Telegram conversation rather than being fetched fresh each step."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.main_menu import main_menu_keyboard
from keyboards.workouts import session_controls_keyboard, workout_detail_keyboard, workout_list_keyboard
from locales import all_translations, t
from services.api_client import BackendAPIError, backend
from services.session import call_authed, get_language
from states import NewWorkout, WorkoutSessionFlow

router = Router(name="workouts")

SEARCH_LIMIT = 6


def _user_args(message_or_callback) -> tuple[int, int, str | None, str | None]:
    user = message_or_callback.from_user
    chat_id = message_or_callback.message.chat.id if isinstance(message_or_callback, CallbackQuery) else message_or_callback.chat.id
    return user.id, chat_id, user.username, user.first_name


# --- List / detail ---------------------------------------------------------------------------


@router.message(F.text.in_(all_translations("menu.workout")))
async def workouts_menu(message: Message) -> None:
    lang = get_language(message.from_user.id)
    uid, chat_id, username, first_name = _user_args(message)
    try:
        workouts = await call_authed(uid, chat_id, username, first_name, lang, backend.list_workouts)
    except BackendAPIError:
        await message.answer(t("common.error", lang))
        return

    if not workouts:
        await message.answer(t("workout.empty", lang))
        return

    await message.answer(t("workout.list_title", lang), reply_markup=workout_list_keyboard(workouts))


@router.callback_query(lambda c: c.data and c.data.startswith("workout:"))
async def show_workout(callback: CallbackQuery) -> None:
    lang = get_language(callback.from_user.id)
    workout_id = callback.data.split(":", 1)[1]
    uid, chat_id, username, first_name = _user_args(callback)

    try:
        workout = await call_authed(uid, chat_id, username, first_name, lang, lambda token: backend.get_workout(token, workout_id))
        names = []
        for we in workout["exercises"]:
            ex = await backend.get_exercise(None, we["exercise_id"], lang)
            names.append(ex["name"])
    except BackendAPIError:
        await callback.message.answer(t("common.error", lang))
        await callback.answer()
        return

    lines = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(names)) or "—"
    text = f"{workout['name']}\n\n" + t("workout.detail_exercises", lang, list=lines)
    if workout["exercises"]:
        await callback.message.answer(text, reply_markup=workout_detail_keyboard(workout_id, lang))
    else:
        await callback.message.answer(text)
    await callback.answer()


# --- Create a workout (/newworkout) -----------------------------------------------------------


@router.message(Command("newworkout"))
async def start_new_workout(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await state.set_state(NewWorkout.name)
    await message.answer(t("workout.new_name_prompt", lang))


@router.message(StateFilter(NewWorkout.name))
async def receive_workout_name(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await state.update_data(name=message.text.strip(), draft=[])
    await state.set_state(NewWorkout.searching)
    await message.answer(t("workout.new_search_prompt", lang))


@router.message(StateFilter(NewWorkout.searching))
async def search_exercise_to_add(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    query = message.text.strip()
    try:
        result = await backend.list_exercises(None, q=query, lang=lang, pageSize=SEARCH_LIMIT)
    except BackendAPIError:
        await message.answer(t("common.error", lang))
        return

    items = result["items"]
    if not items:
        await message.answer(t("workout.new_no_results", lang))
        return

    await state.update_data(last_results={ex["id"]: ex["name"] for ex in items})
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=ex["name"], callback_data=f"addex:{ex['id']}")] for ex in items]
    )
    await message.answer(t("exercises.search_prompt", lang), reply_markup=keyboard)


@router.callback_query(lambda c: c.data and c.data.startswith("addex:"), StateFilter(NewWorkout.searching))
async def add_exercise_to_draft(callback: CallbackQuery, state: FSMContext) -> None:
    lang = get_language(callback.from_user.id)
    exercise_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    name = data.get("last_results", {}).get(exercise_id, exercise_id)

    draft = data.get("draft", [])
    if not any(d["exercise_id"] == exercise_id for d in draft):
        draft.append({"exercise_id": exercise_id, "name": name})
    await state.update_data(draft=draft)

    await callback.message.answer(t("workout.new_added", lang, name=name))
    await callback.answer()


@router.message(Command("done"), StateFilter(NewWorkout.searching))
async def finish_new_workout(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    data = await state.get_data()
    draft = data.get("draft", [])
    if not draft:
        await message.answer(t("workout.new_needs_exercise", lang))
        return

    payload = {
        "name": data["name"],
        "exercises": [{"exercise_id": d["exercise_id"], "order": i} for i, d in enumerate(draft)],
    }
    uid, chat_id, username, first_name = message.from_user.id, message.chat.id, message.from_user.username, message.from_user.first_name
    try:
        await call_authed(uid, chat_id, username, first_name, lang, lambda token: backend.create_workout(token, payload))
    except BackendAPIError:
        await state.clear()
        await message.answer(t("common.error", lang))
        return

    await state.clear()
    await message.answer(
        t("workout.new_created", lang, name=data["name"], count=len(draft)), reply_markup=main_menu_keyboard(lang)
    )


# --- Session tracking --------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("startworkout:"))
async def start_session(callback: CallbackQuery, state: FSMContext) -> None:
    lang = get_language(callback.from_user.id)
    workout_id = callback.data.split(":", 1)[1]
    uid, chat_id, username, first_name = _user_args(callback)

    try:
        workout = await call_authed(uid, chat_id, username, first_name, lang, lambda token: backend.get_workout(token, workout_id))
        session = await call_authed(
            uid, chat_id, username, first_name, lang, lambda token: backend.start_workout(token, workout_id)
        )
        exercises = []
        for we in workout["exercises"]:
            ex = await backend.get_exercise(None, we["exercise_id"], lang)
            exercises.append({"workout_exercise_id": we["id"], "name": ex["name"]})
    except BackendAPIError:
        await callback.message.answer(t("common.error", lang))
        await callback.answer()
        return

    await state.update_data(
        session_id=session["id"], workout_name=workout["name"], exercises=exercises, index=0, set_number=1
    )
    await state.set_state(WorkoutSessionFlow.awaiting_reps)
    await callback.message.answer(
        t("session.started", lang, name=workout["name"], exercise=exercises[0]["name"], set_number=1)
    )
    await callback.answer()


@router.message(StateFilter(WorkoutSessionFlow.awaiting_reps))
async def receive_reps(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    try:
        reps = int(message.text.strip())
    except ValueError:
        await message.answer(t("invalid_number", lang))
        return
    await state.update_data(pending_reps=reps)
    await state.set_state(WorkoutSessionFlow.awaiting_weight)
    await message.answer(t("session.ask_weight", lang))


@router.message(StateFilter(WorkoutSessionFlow.awaiting_weight))
async def receive_weight(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    try:
        weight = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer(t("invalid_number", lang))
        return

    data = await state.get_data()
    exercises = data["exercises"]
    index = data["index"]
    set_number = data["set_number"]
    current = exercises[index]

    payload = {
        "workout_exercise_id": current["workout_exercise_id"],
        "set_number": set_number,
        "reps": data["pending_reps"],
        "weight_kg": weight,
        "completed": True,
    }
    uid, chat_id, username, first_name = message.from_user.id, message.chat.id, message.from_user.username, message.from_user.first_name
    try:
        await call_authed(
            uid, chat_id, username, first_name, lang,
            lambda token: backend.log_set(token, data["session_id"], payload),
        )
    except BackendAPIError:
        await message.answer(t("common.error", lang))
        return

    is_last = index >= len(exercises) - 1
    await message.answer(
        t("session.set_logged", lang, set_number=set_number, reps=data["pending_reps"], weight=weight)
        + "\n\n"
        + t("session.exercise_done_prompt", lang),
        reply_markup=session_controls_keyboard(lang, is_last_exercise=is_last),
    )


@router.callback_query(lambda c: c.data == "sess:more", StateFilter(WorkoutSessionFlow.awaiting_weight))
async def log_another_set(callback: CallbackQuery, state: FSMContext) -> None:
    lang = get_language(callback.from_user.id)
    data = await state.get_data()
    exercise = data["exercises"][data["index"]]
    set_number = data["set_number"] + 1
    await state.update_data(set_number=set_number)
    await state.set_state(WorkoutSessionFlow.awaiting_reps)
    await callback.message.answer(t("session.next_prompt", lang, exercise=exercise["name"], set_number=set_number))
    await callback.answer()


@router.callback_query(lambda c: c.data == "sess:next", StateFilter(WorkoutSessionFlow.awaiting_weight))
async def next_exercise(callback: CallbackQuery, state: FSMContext) -> None:
    lang = get_language(callback.from_user.id)
    data = await state.get_data()
    exercises = data["exercises"]
    index = data["index"] + 1

    if index >= len(exercises):
        await callback.message.answer(t("session.all_exercises_done", lang))
        await callback.answer()
        return

    await state.update_data(index=index, set_number=1)
    await state.set_state(WorkoutSessionFlow.awaiting_reps)
    await callback.message.answer(t("session.next_prompt", lang, exercise=exercises[index]["name"], set_number=1))
    await callback.answer()


@router.callback_query(lambda c: c.data == "sess:finish", StateFilter(WorkoutSessionFlow.awaiting_weight))
async def finish_session(callback: CallbackQuery, state: FSMContext) -> None:
    lang = get_language(callback.from_user.id)
    data = await state.get_data()
    uid, chat_id, username, first_name = _user_args(callback)

    try:
        finished = await call_authed(
            uid, chat_id, username, first_name, lang, lambda token: backend.finish_session(token, data["session_id"])
        )
    except BackendAPIError:
        await callback.message.answer(t("common.error", lang))
        await callback.answer()
        return

    await state.clear()
    await callback.message.answer(
        t(
            "session.finished", lang,
            volume=finished["total_volume_kg"], sets=finished["total_sets"],
            reps=finished["total_reps"], calories=finished["estimated_calories"],
        ),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()
