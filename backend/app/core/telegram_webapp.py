"""Validates Telegram Mini App (Web App) `initData` per Telegram's documented algorithm:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app

The frontend, when opened inside Telegram, gets a `Telegram.WebApp.initData` string from the
Telegram client itself — a query-string of fields (user, auth_date, ...) plus a `hash` that
Telegram computed with the bot's own token. We recompute that hash server-side and compare; if it
doesn't match, the payload wasn't issued by Telegram for this bot. A forged `telegram_id` in the
browser cannot produce a valid hash without the bot token, which is what makes it safe to accept
auth data arriving from client-side JavaScript at all.

Two policies layered on top of Telegram's algorithm (docs/DECISIONS.md):

* **Freshness (D-16).** Telegram does not expire `initData`; we do, at 300 seconds. A real client
  never notices — it receives fresh data every time the Mini App opens — while a captured string
  stops being useful almost immediately.
* **Token rotation (D-18).** Both the current and the previous bot token are accepted, so
  rotating the token at BotFather does not sign every open Mini App out at once.

Replay is handled separately, in `app.core.init_data_guard`, and deliberately is *not* a
one-time-nonce rule — see D-17.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.core.config import get_settings
from app.core.errors import UnauthorizedError

settings = get_settings()


def _signature_matches(data: dict[str, str], received_hash: str, bot_token: str) -> bool:
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, received_hash)


def verify_telegram_webapp_init_data(init_data: str, bot_tokens: str | list[str]) -> dict:
    """Return the parsed fields (with `user` decoded from JSON) if signature and freshness pass.

    `bot_tokens` accepts a single token or a list; every candidate is tried so a rotation window
    keeps working. Raises `UnauthorizedError` otherwise, with a message that distinguishes a bad
    signature from a stale payload — they mean different things and are handled differently.
    """
    if not init_data:
        raise UnauthorizedError("Missing Telegram Web App init data")

    tokens = [bot_tokens] if isinstance(bot_tokens, str) else [t for t in bot_tokens if t]
    if not tokens:
        raise UnauthorizedError("No Telegram bot token configured to verify against")

    data = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise UnauthorizedError("Invalid Telegram Web App init data")

    if not any(_signature_matches(data, received_hash, token) for token in tokens):
        raise UnauthorizedError("Invalid Telegram Web App init data signature")

    auth_date = data.get("auth_date")
    if auth_date is None or not auth_date.isdigit():
        raise UnauthorizedError("Telegram Web App init data has no usable auth_date")
    if time.time() - int(auth_date) > settings.init_data_max_age_seconds:
        raise UnauthorizedError("Telegram Web App init data has expired — reopen the app")

    if "user" in data:
        try:
            data["user"] = json.loads(data["user"])
        except (json.JSONDecodeError, TypeError) as exc:
            raise UnauthorizedError("Invalid Telegram Web App user payload") from exc

    return data
