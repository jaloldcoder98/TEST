from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str
    backend_api_url: str = "http://backend:8000/api/v1"

    # Public HTTPS URL of the frontend, used to launch it as a Telegram Mini App (a `web_app`
    # button — Telegram requires HTTPS and refuses http://, so a plain "http://backend:8000"-style
    # Docker-internal address won't work here even in dev; use a tunnel (e.g. ngrok) or a real
    # deployment, and point this at that public URL. Empty means "not configured yet" — /start and
    # the persistent menu button both fall back to the classic text-command flow instead of
    # showing a broken/absent button, rather than crashing on FastAPI-side WebAppInfo validation.
    frontend_url: str = ""


settings = BotSettings()
