from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from locales import t


def workout_list_keyboard(workouts: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=w["name"], callback_data=f"workout:{w['id']}")] for w in workouts]
    )


def workout_detail_keyboard(workout_id: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("workout.start_button", lang), callback_data=f"startworkout:{workout_id}")]]
    )


def session_controls_keyboard(lang: str, *, is_last_exercise: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=t("session.log_another_set", lang), callback_data="sess:more")]]
    if not is_last_exercise:
        rows.append([InlineKeyboardButton(text=t("session.next_exercise", lang), callback_data="sess:next")])
    rows.append([InlineKeyboardButton(text=t("session.finish", lang), callback_data="sess:finish")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
