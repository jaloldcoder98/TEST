"""Per-Telegram-user session cache. The bot process holds access/refresh tokens in memory
rather than a DB of its own (spec.md §61 rule 11: no duplicated business logic / storage) — on
restart the cache is empty and the next interaction just re-authenticates via POST /auth/telegram,
which is idempotent for an already-linked telegram_id (see auth_service.telegram_auth), so
nothing is lost except needing one extra round-trip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from services.api_client import BackendAPIError, backend

T = TypeVar("T")


@dataclass
class Session:
    access_token: str
    refresh_token: str
    language: str


_SESSIONS: dict[int, Session] = {}


async def ensure_session(telegram_id: int, chat_id: int, username: str | None, first_name: str | None, language: str) -> Session:
    cached = _SESSIONS.get(telegram_id)
    if cached is not None:
        return cached
    tokens = await backend.telegram_auth(telegram_id, chat_id, username, first_name, language)
    session = Session(access_token=tokens["access_token"], refresh_token=tokens["refresh_token"], language=language)
    _SESSIONS[telegram_id] = session
    return session


def set_session(telegram_id: int, access_token: str, refresh_token: str, language: str) -> None:
    _SESSIONS[telegram_id] = Session(access_token=access_token, refresh_token=refresh_token, language=language)


def get_language(telegram_id: int, default: str = "uz") -> str:
    session = _SESSIONS.get(telegram_id)
    return session.language if session else default


def set_language(telegram_id: int, language: str) -> None:
    if telegram_id in _SESSIONS:
        _SESSIONS[telegram_id].language = language


async def call_authed(
    telegram_id: int, chat_id: int, username: str | None, first_name: str | None, language: str, fn: Callable[[str], Awaitable[T]]
) -> T:
    """Runs `fn(access_token)`, transparently recovering from an expired/invalid access token:
    first by rotating the cached refresh token, then — if that's also gone — by re-authenticating
    from scratch. Callers never have to think about token lifetime."""
    session = await ensure_session(telegram_id, chat_id, username, first_name, language)
    try:
        return await fn(session.access_token)
    except BackendAPIError as exc:
        if exc.status_code != 401:
            raise
        try:
            tokens = await backend.refresh(session.refresh_token)
            set_session(telegram_id, tokens["access_token"], tokens["refresh_token"], session.language)
        except BackendAPIError:
            tokens = await backend.telegram_auth(telegram_id, chat_id, username, first_name, session.language)
            set_session(telegram_id, tokens["access_token"], tokens["refresh_token"], session.language)
        return await fn(_SESSIONS[telegram_id].access_token)
