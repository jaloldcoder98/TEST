"""Central application settings, loaded from environment variables (.env in dev).

Nothing here is hardcoded per spec rule "do not hardcode secrets" (spec.md §61) — every
credential and tunable comes from the environment, with safe (non-secret) local defaults so
`docker compose up` works out of the box in development.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Core ---
    environment: str = "development"
    debug: bool = True

    # --- Database ---
    database_url: str = "postgresql+asyncpg://gym:gym@postgres:5432/gym"

    # --- Redis / workers ---
    redis_url: str = "redis://redis:6379/0"

    # --- Auth ---
    jwt_secret: str = "change-me-in-.env"
    jwt_refresh_secret: str = "change-me-too-in-.env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    # --- AI ---
    openai_api_key: str | None = None
    ai_model: str = "gpt-4o-mini"

    # --- Telegram ---
    telegram_bot_token: str | None = None

    # --- Object storage (food photos) ---
    storage_endpoint: str | None = None
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_bucket: str | None = None

    # --- Pagination defaults (spec §40: never return 1300+ exercises by default) ---
    default_page_size: int = 20
    max_page_size: int = 100

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
