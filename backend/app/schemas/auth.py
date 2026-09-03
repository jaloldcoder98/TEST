from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Language


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    language: Language = Language.UZ


class LoginRequest(BaseModel):
    username: str
    password: str


class TelegramAuthRequest(BaseModel):
    """POST /auth/telegram — frictionless Telegram-side auth (spec.md §30: one account works on
    both web and the bot). If `telegram_id` is already linked, this just re-issues tokens for
    that account; otherwise it auto-creates a bot-only account (no password) bound to it.
    """

    telegram_id: int
    chat_id: int
    telegram_username: str | None = None
    first_name: str | None = None
    language: Language = Language.UZ


class TelegramWebAppAuthRequest(BaseModel):
    """POST /auth/telegram-webapp — auth entry point for the Telegram Mini App. `init_data` is
    the raw `Telegram.WebApp.initData` string the frontend reads from the Telegram client; the
    server verifies its signature (app/core/telegram_webapp.py) before trusting anything in it,
    since — unlike the bot calling /auth/telegram directly — this arrives from client-side JS.
    """

    init_data: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
