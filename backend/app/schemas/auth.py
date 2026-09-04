from pydantic import BaseModel, Field

from app.models.enums import Language


class TelegramAuthRequest(BaseModel):
    """POST /auth/telegram — the bot's door.

    Carries no signature, so the route requires the shared secret header instead (D-20). Idempotent
    per `telegram_id`: an already-linked id signs in, an unknown one is provisioned.
    """

    telegram_id: int
    chat_id: int
    telegram_username: str | None = None
    first_name: str | None = None
    language: Language = Language.UZ


class TelegramWebAppAuthRequest(BaseModel):
    """POST /auth/telegram-webapp — the Mini App's door. `init_data` is the raw
    `Telegram.WebApp.initData` string; its signature is verified against the bot token before
    anything inside it is trusted (app/core/telegram_webapp.py)."""

    init_data: str = Field(min_length=1)


class SessionResponse(BaseModel):
    """What a browser gets. No refresh token: it goes out as an httpOnly cookie the page cannot
    read (D-12, D-13). `csrf_token` is held in memory and echoed in `X-CSRF-Token` on refresh."""

    access_token: str
    csrf_token: str
    token_type: str = "bearer"


class BotSessionResponse(BaseModel):
    """What the bot gets. It has no cookie jar, so the refresh token comes in the body and the
    bot stores it itself — acceptable because the bot is a trusted server-side process, not a
    browser exposed to XSS."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
