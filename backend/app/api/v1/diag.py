"""Phase 0 diagnostics: measure how a Telegram Mini App's WebView actually behaves.

This module exists to answer one question empirically, before any auth code is written:
**does the cookie session model in `docs/DECISIONS.md` (D-13) survive each Telegram client?**
Telegram embeds a Mini App as a top-level document in a native WebView on iOS/Android/Desktop,
but as a cross-site `<iframe>` on Telegram Web — where a third-party cookie may be blocked
(Safari), partitioned (Firefox), or require the `Partitioned` attribute (Chrome). Guessing which
would be the most expensive mistake in the project, so we measure instead.

Nothing here authenticates anybody. It issues no tokens, touches no database, and creates no
account: it sets a throwaway cookie shaped exactly like the real one will be, reports what the
server saw, and reports whether an `initData` string verifies — facts only.

**This router is mounted only when `settings.debug` is true** (see `router.py`), so it cannot
exist in a production process at all. It is removed once Phase 0 is signed off — see
`docs/TELEGRAM_WEBVIEW_MATRIX.md`.
"""

from __future__ import annotations

import json
import secrets
import time
from urllib.parse import parse_qsl

from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.telegram_webapp import verify_telegram_webapp_init_data

router = APIRouter()
settings = get_settings()

# Shaped exactly like the refresh cookie D-13 specifies, so what we measure here is what the
# real thing will do. `__Host-` forbids a Domain attribute and requires Secure + Path=/;
# SameSite=None is what makes it available inside Telegram Web's cross-site iframe at all, and
# Partitioned (CHIPS) is what keeps Chrome from dropping it once third-party cookies are gone.
COOKIE_NAME = "__Host-gym_diag"
COOKIE_ATTRS = "Path=/; Secure; HttpOnly; SameSite=None; Partitioned; Max-Age=3600"


def _mask(value: str | None, keep: int = 3) -> str | None:
    """Never echo a full identifier back (D-146) — enough to recognise, not enough to reuse."""
    if not value:
        return None
    text = str(value)
    return text[-keep:].rjust(len(text), "*") if len(text) > keep else "*" * len(text)


def _observed(request: Request) -> dict:
    """What the server actually received. `Origin`/`Referer` are the interesting ones: D-19 makes
    them a *secondary* CSRF layer precisely because we do not yet know whether every Telegram
    client sends them."""
    headers = request.headers
    return {
        "origin": headers.get("origin"),
        "referer": headers.get("referer"),
        "sec_fetch_site": headers.get("sec-fetch-site"),
        "sec_fetch_mode": headers.get("sec-fetch-mode"),
        "sec_fetch_dest": headers.get("sec-fetch-dest"),
        "user_agent": headers.get("user-agent"),
        "cookie_header_present": "cookie" in headers,
        "cookie_names": sorted(request.cookies.keys()),
        "diag_cookie_present": COOKIE_NAME in request.cookies,
    }


@router.get("/env")
async def diag_env(request: Request) -> dict:
    return {"observed": _observed(request), "server_time": int(time.time())}


@router.post("/cookie")
async def diag_set_cookie(request: Request, response: Response) -> dict:
    """Set the probe cookie and hand back a CSRF token, mirroring the double-submit scheme in
    D-19. Set-Cookie is written by hand rather than via `response.set_cookie` so the exact
    attribute string is pinned here and visible in the test report — `Partitioned` in particular
    is not supported uniformly across Starlette versions."""
    value = secrets.token_urlsafe(16)
    response.headers.append("Set-Cookie", f"{COOKIE_NAME}={value}; {COOKIE_ATTRS}")
    return {
        "set_cookie_sent": True,
        "cookie_name": COOKIE_NAME,
        "cookie_attributes": COOKIE_ATTRS,
        "csrf_token": secrets.token_urlsafe(16),
        "observed": _observed(request),
    }


@router.get("/cookie")
async def diag_read_cookie(request: Request) -> dict:
    """The whole question in one call: did the cookie come back on a later request?"""
    present = COOKIE_NAME in request.cookies
    return {
        "cookie_returned": present,
        # Presence, never the value — a returned cookie is the signal; its contents are not.
        "cookie_value_masked": _mask(request.cookies.get(COOKIE_NAME), keep=4) if present else None,
        "observed": _observed(request),
    }


@router.delete("/cookie")
async def diag_clear_cookie(response: Response) -> dict:
    response.headers.append("Set-Cookie", f"{COOKIE_NAME}=; Path=/; Secure; HttpOnly; SameSite=None; Partitioned; Max-Age=0")
    return {"cleared": True}


@router.post("/initdata")
async def diag_init_data(request: Request, payload: dict) -> dict:
    """Verify an `initData` string and report the sub-checks separately.

    Signature and freshness are reported apart from each other because they fail for different
    reasons and D-16/D-17 treat them differently: a bad signature is an attack, an expired
    `auth_date` is just a stale tab. `auth_date` is read straight off the raw string for the age
    report — it is not a secret, and reading it does not imply the payload is trusted.
    """
    init_data = payload.get("init_data") or ""
    if not settings.telegram_bot_token:
        return {"checked": False, "reason": "TELEGRAM_BOT_TOKEN is not configured on this server"}

    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    auth_date = fields.get("auth_date")
    age_seconds = int(time.time()) - int(auth_date) if auth_date and auth_date.isdigit() else None

    signature_valid, failure = True, None
    try:
        verified = verify_telegram_webapp_init_data(init_data, settings.telegram_bot_token)
    except AppError as exc:
        signature_valid, failure, verified = False, exc.message, None

    user = (verified or {}).get("user") or {}
    if not user and fields.get("user"):
        try:
            user = json.loads(fields["user"])
        except (json.JSONDecodeError, TypeError):
            user = {}

    return {
        "checked": True,
        "init_data_present": bool(init_data),
        "init_data_length": len(init_data),
        "signature_valid": signature_valid,
        "failure_reason": failure,
        "auth_date": auth_date,
        "age_seconds": age_seconds,
        # D-16: the 300s window this project settled on, reported independently of the
        # verifier's own (currently 24h) window so the report shows what the new rule would do.
        "within_300s_window": (age_seconds is not None and 0 <= age_seconds <= 300),
        "telegram_id_masked": _mask(user.get("id")),
        "telegram_platform": fields.get("platform"),
        "observed": _observed(request),
    }
