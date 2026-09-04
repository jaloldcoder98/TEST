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

    # --- Auth (docs/DECISIONS.md D-12, D-13, D-14) ---
    jwt_secret: str = "change-me-in-.env"
    jwt_refresh_secret: str = "change-me-too-in-.env"
    jwt_algorithm: str = "HS256"
    # Short-lived by design: the access token lives only in the page's memory (D-12), so a long
    # TTL buys nothing and costs everything if one leaks.
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    # Admins get a tighter envelope than ordinary users (D: 5-round Q16.2) — the account that can
    # change roles and run bulk imports should not sit around valid for a week.
    admin_access_token_expire_minutes: int = 10
    admin_refresh_token_expire_hours: int = 24

    # Refresh cookie (D-13). `__Host-` forbids a Domain attribute and requires Secure + Path=/;
    # SameSite=None is what lets it exist at all inside Telegram Web's cross-site iframe, and
    # Partitioned (CHIPS) is what keeps Chrome from dropping it once third-party cookies are gone.
    # `cookie_secure` is configurable only so a plain-HTTP local run can still exercise the flow;
    # production must leave it true, and `__Host-` is dropped along with it since the prefix
    # requires Secure.
    cookie_secure: bool = True

    # --- Telegram (D-16, D-17, D-18, D-20) ---
    telegram_bot_token: str | None = None
    # Accepted alongside the current token during a rotation window, so rotating the bot token
    # does not invalidate every open Mini App at once.
    telegram_bot_token_previous: str | None = None
    # Telegram's own initData carries no expiry; this is our freshness policy. 300s is short
    # enough to make a captured string near-useless and long enough that a real client, which
    # gets fresh initData every time the Mini App opens, never notices.
    init_data_max_age_seconds: int = 300
    # D-17 is explicit that this is NOT a one-time nonce: the same legitimate initData may be
    # presented again on a reload. We only throttle *abusive* repetition of one identical payload.
    init_data_max_repeats: int = 30
    init_data_repeat_window_seconds: int = 300
    # Shared secret the bot sends on /auth/telegram (D-20). Without it that endpoint would accept
    # any telegram_id from anyone who can reach it.
    bot_shared_secret: str | None = None
    # Telegram ids promoted to super_admin at startup (D-32). Promote-only, never demote.
    bootstrap_admin_telegram_ids: str = ""

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"
    # The Mini App's own public origin. Read here (not just by the bot) because CSRF's Origin
    # check needs to know which origin is legitimately ours — see app/core/csrf.py.
    frontend_url: str = ""

    # --- AI ---
    openai_api_key: str | None = None
    ai_model: str = "gpt-4o-mini"

    # --- Object storage (food photos) ---
    storage_endpoint: str | None = None
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_bucket: str | None = None

    # --- Pagination defaults (spec §40: never return 1300+ exercises by default) ---
    default_page_size: int = 20
    max_page_size: int = 100

    # --- Rate limiting (spec §37: brute-force/credential-stuffing protection on auth) ---
    # Disabled only by the test suite (tests/conftest.py sets RATE_LIMIT_ENABLED=false before the
    # app is imported) so dozens of tests reusing one client/IP don't trip real limits.
    rate_limit_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def bootstrap_admin_ids(self) -> list[int]:
        """Parsed `BOOTSTRAP_ADMIN_TELEGRAM_IDS`. Malformed entries are skipped rather than
        crashing startup — a typo in one id should not take the whole service down."""
        ids = []
        for raw in self.bootstrap_admin_telegram_ids.split(","):
            raw = raw.strip()
            if raw.isdigit():
                ids.append(int(raw))
        return ids

    @property
    def telegram_bot_tokens(self) -> list[str]:
        """Current token first, then the previous one if a rotation is in progress (D-18)."""
        return [t for t in (self.telegram_bot_token, self.telegram_bot_token_previous) if t]


@lru_cache
def get_settings() -> Settings:
    return Settings()
