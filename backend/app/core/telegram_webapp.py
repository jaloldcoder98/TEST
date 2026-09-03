# TODO(webapp-first): Audit §1.2 — _MAX_AGE_SECONDS is 24h, so a captured initData string stays usable for a
# whole day. Tighten to ~1h and make it configurable via app/core/config.py.
#
# Also needed for TZ §24 deep links: initData carries `start_param` when the Mini App is
# opened via t.me/<bot>?startapp=nutrition. Parse and return it so the frontend can route
# the user to the right screen on first paint.
# See docs/WEBAPP_FIRST_AUDIT.md for the full plan.

"""Validates Telegram Mini App (Web App) `initData` per Telegram's documented algorithm:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app

The frontend, when opened inside Telegram, gets a `Telegram.WebApp.initData` string from the
Telegram client itself — it's a query-string of fields (user, auth_date, ...) plus a `hash` that
Telegram computed with the bot's own token. We recompute that hash server-side and compare; if it
doesn't match, the payload wasn't actually issued by Telegram for this bot; a forged `telegram_id`
in the browser can't produce a hash without knowing the bot token, so — unlike the bot-side
`/auth/telegram` (trusted because only our own bot process can call it, from an update it read
straight off Telegram's servers) — this is the check that makes it safe to accept auth data
coming directly from client-side JavaScript.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.core.errors import UnauthorizedError

# initData is meant to be used immediately after the Mini App opens — this bounds how long a
# captured/replayed initData string stays accepted (Telegram itself doesn't enforce this; it's
# our own replay-window policy).
_MAX_AGE_SECONDS = 24 * 60 * 60


def verify_telegram_webapp_init_data(init_data: str, bot_token: str) -> dict:
    """Returns the parsed initData fields (with `user` decoded from JSON) if the signature and
    freshness check pass. Raises UnauthorizedError otherwise."""
    if not init_data:
        raise UnauthorizedError("Missing Telegram Web App init data")

    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise UnauthorizedError("Invalid Telegram Web App init data")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise UnauthorizedError("Invalid Telegram Web App init data signature")

    auth_date = data.get("auth_date")
    if auth_date is None or time.time() - int(auth_date) > _MAX_AGE_SECONDS:
        raise UnauthorizedError("Telegram Web App init data has expired — reopen the app")

    if "user" in data:
        try:
            data["user"] = json.loads(data["user"])
        except (json.JSONDecodeError, TypeError) as exc:
            raise UnauthorizedError("Invalid Telegram Web App user payload") from exc

    return data
