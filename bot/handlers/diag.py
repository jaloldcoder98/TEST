"""Phase 0 only: a `/diag` command that opens the Telegram WebView diagnostics page.

Without this, testing means repointing `FRONTEND_URL` at the diagnostics page, restarting the
bot, and remembering to put it back afterwards — three chances to get it wrong, on three
devices. Here `FRONTEND_URL` stays the normal frontend URL and `/diag` just derives the
diagnostics path from it, so the app and the probe can be opened side by side.

Deleted together with the rest of the harness when Phase 0 closes — see
`docs/TELEGRAM_WEBVIEW_MATRIX.md` §7.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from config import settings

router = Router(name="diag")

DIAG_PATH = "/_diag/webview.html"


def diagnostics_url() -> str | None:
    """The diagnostics page URL, or None if `FRONTEND_URL` can't launch a Web App.

    Telegram rejects a `web_app` button whose url isn't https:// outright, so an unset or
    http:// value has to be caught here rather than surfacing as a confusing API error.
    """
    base = (settings.frontend_url or "").strip()
    if not base.startswith("https://"):
        return None
    # Tolerate FRONTEND_URL already pointing straight at the page — an earlier revision of the
    # runbook told testers to set it that way, and silently doubling the path would be worse
    # than accepting both forms.
    return base if base.rstrip("/").endswith(DIAG_PATH) else base.rstrip("/") + DIAG_PATH


@router.message(Command("diag"))
async def diag_command(message: Message) -> None:
    url = diagnostics_url()
    if url is None:
        await message.answer(
            "Diagnostika sahifasini ochib bo'lmadi: .env dagi FRONTEND_URL https:// bilan "
            "boshlanadigan ommaviy manzil bo'lishi kerak (masalan ngrok tunneli). "
            "Qo'llanma: docs/PHASE0_TEST_RUNBOOK.md"
        )
        return

    await message.answer(
        "0-bosqich diagnostikasi.\n\n"
        "1-tugmani bosing → Mini App'ni butunlay yoping → qaytadan oching → 2-tugma → "
        "3-tugma → 4-tugma bilan natijani nusxalang.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔬 Diagnostikani ochish", web_app=WebAppInfo(url=url))]]
        ),
    )
