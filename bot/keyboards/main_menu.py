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
