"""Profile/Settings: shows the linked account and lets the user change their bot language,
persisted to the backend the same way the web app's profile settings do (PATCH /users/me)."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from locales import LOCALES, all_translations, t
from services.api_client import BackendAPIError, backend
from services.session import call_authed, get_language, set_language

router = Router(name="profile")

_LANGUAGE_LABELS = {"uz": "O'zbekcha", "ru": "Русский", "en": "English"}

# A separate callback_data prefix from the /start onboarding language picker (keyboards/language.py
# uses "lang:") — the two flows fire in very different contexts (no session yet vs. an existing,
# already-linked user), and reusing one prefix would make aiogram's first-match-wins routing
# ambiguous between handlers/start.py and this handler.
_SETTINGS_LANGUAGE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en"),
        ]
    ]
)


@router.message(F.text.in_(all_translations("menu.profile") | all_translations("menu.settings")))
async def profile_menu(message: Message) -> None:
    lang = get_language(message.from_user.id)
    user = message.from_user
    try:
        me = await call_authed(user.id, message.chat.id, user.username, user.first_name, lang, backend.get_me)
    except BackendAPIError:
        await message.answer(t("common.error", lang))
        return

    text = t("profile.title", lang, username=me["username"], language=_LANGUAGE_LABELS.get(lang, lang))
    await message.answer(text, reply_markup=_SETTINGS_LANGUAGE_KEYBOARD)


@router.callback_query(lambda c: c.data and c.data.startswith("setlang:"))
async def change_language(callback: CallbackQuery) -> None:
    new_lang = callback.data.split(":", 1)[1]
    user = callback.from_user
    if new_lang not in LOCALES:
        await callback.answer()
        return

    current_lang = get_language(user.id)
    try:
        await call_authed(
            user.id, callback.message.chat.id, user.username, user.first_name, current_lang,
            lambda token: backend.update_me(token, {"language": new_lang}),
        )
    except BackendAPIError:
        await callback.answer(t("common.error", current_lang), show_alert=True)
        return

    set_language(user.id, new_lang)
    await callback.message.answer(t("common.saved", new_lang))
    await callback.answer()
