"""/link — attach an *existing* web account to this Telegram account, instead of the bot-only
one auto-provisioned on first /start. Validates credentials via the same POST /auth/login the
website uses, then POST /users/me/link-telegram with the resulting token."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.main_menu import main_menu_keyboard
from locales import t
from services.api_client import BackendAPIError, backend
from services.session import get_language, set_session
from states import LinkAccount

router = Router(name="link")


@router.message(Command("link"))
async def start_link(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await state.set_state(LinkAccount.username)
    await message.answer(t("link.ask_username", lang))


@router.message(LinkAccount.username)
async def receive_username(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await state.update_data(username=message.text.strip())
    await state.set_state(LinkAccount.password)
    await message.answer(t("link.ask_password", lang))


@router.message(LinkAccount.password)
async def receive_password(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    data = await state.get_data()
    username = data["username"]
    password = message.text

    # The password never needs to stay in the chat log.
    try:
        await message.delete()
    except Exception:
        pass

    try:
        tokens = await backend.login(username, password)
        await backend.link_telegram(
            tokens["access_token"], message.from_user.id, message.chat.id, message.from_user.username
        )
    except BackendAPIError as exc:
        await state.clear()
        if exc.code == "TELEGRAM_ALREADY_LINKED":
            await message.answer(t("link.already_linked", lang))
        else:
            await message.answer(t("link.invalid", lang))
        return

    set_session(message.from_user.id, tokens["access_token"], tokens["refresh_token"], lang)
    await state.clear()
    await message.answer(t("link.success", lang, username=username), reply_markup=main_menu_keyboard(lang))
