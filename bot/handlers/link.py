"""/link — kept as a command, but there is nothing left to link.

It used to attach an existing web account to a Telegram account by asking for the website
username and password. With Telegram as the only identity (docs/DECISIONS.md D-10) the Telegram
account *is* the account: whoever opens the bot or the Mini App first creates it, and both
surfaces sign into the same one.

The command survives rather than being deleted because people who used it before will type it
again, and "unknown command" would leave them wondering what happened to their data (D: 5-round
E4). It now explains, and points at the app.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from config import settings
from keyboards.main_menu import main_menu_keyboard
from locales import t
from services.session import get_language

router = Router(name="link")


@router.message(Command("link"))
async def link_command(message: Message, state: FSMContext) -> None:
    # Clear any state left over from an interrupted flow, so /link is always a safe way out.
    await state.clear()
    lang = get_language(message.from_user.id)

    if settings.frontend_url.startswith("https://"):
        await message.answer(
            t("link.already_connected", lang),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=t("start.open_app", lang), web_app=WebAppInfo(url=settings.frontend_url))]
                ]
            ),
        )
        return

    await message.answer(t("link.already_connected", lang), reply_markup=main_menu_keyboard(lang))
