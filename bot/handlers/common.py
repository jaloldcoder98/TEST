"""/cancel — universal escape hatch out of any FSM flow (link account, new workout, an
in-progress session, logging food/weight)."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.main_menu import main_menu_keyboard
from locales import t
from services.session import get_language

router = Router(name="common")


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    lang = get_language(message.from_user.id)
    await state.clear()
    await message.answer(t("common.cancelled", lang), reply_markup=main_menu_keyboard(lang))
