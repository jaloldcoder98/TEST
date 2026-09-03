"""cmd_start (handlers/start.py) has two branches depending on whether FRONTEND_URL is configured
(config.settings.frontend_url) — the Mini App "Open App" button, or the original language-picker
fallback. monkeypatching the attribute on the shared `settings` singleton (rather than the env
var) is enough since handlers/start.py reads it at call time, not at import time."""

from aiogram.types import InlineKeyboardMarkup

from handlers import start as start_module
from tests.conftest import make_message


async def test_start_shows_open_app_button_when_frontend_url_configured(monkeypatch) -> None:
    monkeypatch.setattr(start_module.settings, "frontend_url", "https://gymapp.example.com")
    message = make_message(text="/start")

    await start_module.cmd_start(message)

    assert len(message.calls) == 1
    markup = message.calls[0]["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    button = markup.inline_keyboard[0][0]
    assert button.web_app is not None
    assert button.web_app.url == "https://gymapp.example.com"


async def test_start_falls_back_to_language_picker_when_frontend_url_unset(monkeypatch) -> None:
    monkeypatch.setattr(start_module.settings, "frontend_url", "")
    message = make_message(text="/start")

    await start_module.cmd_start(message)

    assert len(message.calls) == 1
    markup = message.calls[0]["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    # The language keyboard has three buttons (uz/ru/en) in one row, none of them a web_app button.
    buttons = markup.inline_keyboard[0]
    assert len(buttons) == 3
    assert all(b.web_app is None for b in buttons)
    assert all(b.callback_data and b.callback_data.startswith("lang:") for b in buttons)


async def test_start_falls_back_when_frontend_url_is_not_https(monkeypatch) -> None:
    # Telegram refuses a web_app button whose url isn't https:// — a plain http:// value (e.g.
    # someone pointing this straight at the Docker-internal frontend by mistake) must degrade to
    # the fallback rather than attempting a button Telegram would reject.
    monkeypatch.setattr(start_module.settings, "frontend_url", "http://localhost:3000")
    message = make_message(text="/start")

    await start_module.cmd_start(message)

    markup = message.calls[0]["reply_markup"]
    assert all(b.web_app is None for b in markup.inline_keyboard[0])
