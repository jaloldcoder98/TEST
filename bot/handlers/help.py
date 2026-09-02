from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from locales import t
from services.session import get_language

router = Router(name="help")

_COMMANDS = [
    "newworkout",
    "done",
    "logmeal",
    "logweight",
    "link",
    "cancel",
]


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    lang = get_language(message.from_user.id)
    lines = [f"/{cmd}" for cmd in _COMMANDS]
    await message.answer("\n".join(lines) + "\n\n" + t("link.usage", lang))
