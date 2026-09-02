from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from locales import t

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def meal_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=t(f"nutrition.{m}", lang), callback_data=f"meal:{m}") for m in MEAL_TYPES]
    return InlineKeyboardMarkup(inline_keyboard=[[b] for b in buttons])
