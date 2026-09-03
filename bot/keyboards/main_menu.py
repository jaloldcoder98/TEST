# TODO(webapp-first): TZ §2/§43 — this seven-button reply keyboard *is* the duplicate bot UI the spec rules out.
# It should become a single web_app button ("🚀 GYM APP'NI OCHISH" / "ОТКРЫТЬ" / "OPEN"),
# localized per user. keyboards/workouts.py and keyboards/nutrition.py retire with the
# handlers that use them (audit §2).
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from locales import t


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Main menu per spec.md §5: Workout / Exercises / Progress / Nutrition / AI Coach /
    Profile / Settings."""
    rows = [
        [KeyboardButton(text=t("menu.workout", lang)), KeyboardButton(text=t("menu.exercises", lang))],
        [KeyboardButton(text=t("menu.progress", lang)), KeyboardButton(text=t("menu.nutrition", lang))],
        [KeyboardButton(text=t("menu.ai_coach", lang))],
        [KeyboardButton(text=t("menu.profile", lang)), KeyboardButton(text=t("menu.settings", lang))],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
