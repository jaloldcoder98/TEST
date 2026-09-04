"""Authentication routes (docs/DECISIONS.md D-10 … D-21).

Two doors in, and they hand back different shapes on purpose:

* the **Mini App** gets an access token plus a CSRF token in the body, and its refresh token as an
  httpOnly cookie it can never read (D-12, D-13);
* the **bot** gets both tokens in the body, because it has no cookie jar and is a trusted
  server-side process rather than a browser exposed to XSS.

The cookie is used by `/refresh` and `/logout` and nowhere else, which is what keeps this API's
CSRF surface down to two endpoints (D-19).
"""

import hmac

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cookies import clear_refresh_cookie, read_refresh_cookie, set_refresh_cookie
from app.core.csrf import verify_csrf
from app.core.db import get_db
from app.core.errors import AppError, UnauthorizedError
from app.core.rate_limit import rate_limit
from app.core.security import csrf_token_for
from app.schemas.auth import (
    BotSessionResponse,
    SessionResponse,
    TelegramAuthRequest,
    TelegramWebAppAuthRequest,
)
from app.services import auth_service

router = APIRouter()
settings = get_settings()

# Per client IP (app/core/rate_limit.py). The Telegram entry points get real headroom because a
# legitimate client hits them often — token rotation, reconnects, reopening the Mini App — and
# because behind carrier-grade NAT many real users share one address (D-150).
_REFRESH_LIMIT = Depends(rate_limit("refresh", max_requests=60, window_seconds=60))
_TELEGRAM_AUTH_LIMIT = Depends(rate_limit("telegram_auth", max_requests=60, window_seconds=60))
_TELEGRAM_WEBAPP_AUTH_LIMIT = Depends(rate_limit("telegram_webapp_auth", max_requests=60, window_seconds=60))


def _require_bot_secret(x_bot_secret: str | None = Header(default=None)) -> None:
    """Gate for the bot's door (D-20).

    `/auth/telegram` takes a `telegram_id` on trust — there is no signature to verify — so without
    this header anyone who can reach the endpoint could log in as any Telegram user. Compared in
    constant time, and refused outright when no secret is configured rather than falling back to
    "allow", so a missing configuration fails closed.
    """
    if not settings.bot_shared_secret:
        raise AppError("BOT_AUTH_NOT_CONFIGURED", "Bot authentication is not configured on this server", 503)
    if not x_bot_secret or not hmac.compare_digest(x_bot_secret, settings.bot_shared_secret):
        raise UnauthorizedError("Invalid bot credentials")


def _session_response(response: Response, session) -> SessionResponse:
    set_refresh_cookie(response, session.refresh_token, session.refresh_max_age_seconds)
    return SessionResponse(access_token=session.access_token, csrf_token=session.csrf_token)


@router.post("/telegram-webapp", response_model=SessionResponse, dependencies=[_TELEGRAM_WEBAPP_AUTH_LIMIT])
async def telegram_webapp_auth(
    data: TelegramWebAppAuthRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """The Mini App's only way in — and the fallback the whole session model leans on: when the
    refresh cookie is missing or rejected, the client silently posts fresh `initData` here and
    carries on (D-15, invariant 16)."""
    return _session_response(response, await auth_service.telegram_webapp_auth(db, data.init_data))


@router.post(
    "/telegram",
    response_model=BotSessionResponse,
    dependencies=[_TELEGRAM_AUTH_LIMIT, Depends(_require_bot_secret)],
)
async def bot_telegram_auth(data: TelegramAuthRequest, db: AsyncSession = Depends(get_db)) -> BotSessionResponse:
    session = await auth_service.bot_telegram_auth(db, data)
    return BotSessionResponse(access_token=session.access_token, refresh_token=session.refresh_token)


@router.post("/refresh", response_model=SessionResponse, dependencies=[_REFRESH_LIMIT])
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """Rotate the browser's session.

    A missing cookie is a 401 rather than an error worth explaining: it is the ordinary state on
    Telegram Web or Safari, where the cookie may never have been stored at all, and the client's
    correct response is to re-authenticate with fresh `initData`, not to show a failure.
    """
    token = read_refresh_cookie(request)
    if not token:
        raise UnauthorizedError("No refresh session")

    verify_csrf(request, csrf_token_for(token))
    session = await auth_service.refresh(db, token)
    return _session_response(response, session)


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    token = read_refresh_cookie(request)
    if token:
        # CSRF still applies: a forced logout is a real (if minor) attack, and the check costs
        # nothing here. An unknown token is a silent no-op — logout must not report what existed.
        verify_csrf(request, csrf_token_for(token))
        await auth_service.logout(db, token)
    clear_refresh_cookie(response)
    return {"success": True}


@router.post("/bot/refresh", response_model=BotSessionResponse, dependencies=[_REFRESH_LIMIT, Depends(_require_bot_secret)])
async def bot_refresh(data: dict, db: AsyncSession = Depends(get_db)) -> BotSessionResponse:
    """The bot's rotation endpoint: same reuse detection and family revocation as the browser's,
    but the token travels in the body because the bot has no cookies. Guarded by the shared
    secret, so a stolen refresh token alone is not enough to use it."""
    token = data.get("refresh_token")
    if not token:
        raise UnauthorizedError("No refresh token provided")
    session = await auth_service.refresh(db, token)
    return BotSessionResponse(access_token=session.access_token, refresh_token=session.refresh_token)
