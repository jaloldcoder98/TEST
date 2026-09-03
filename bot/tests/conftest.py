"""Shared fakes for handler unit tests (Phase 8). The bot has no test client the way the FastAPI
backend does — aiogram dispatches real Telegram Message/CallbackQuery objects to handler
functions, which are plain `async def`s that take (event, state, ...) — so the cheapest, most
direct way to unit test a handler is to call it directly with lightweight fakes that satisfy the
same attributes/methods the handler actually touches (`.text`, `.from_user`, `.answer()`, an
FSMContext with get_data/update_data/set_state/clear), and to monkeypatch `services.api_client.backend`
so no real network call happens. This mirrors the backend's own `_StubProvider` pattern in
tests/test_ai.py: fake the boundary, exercise the real logic.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest


class FakeFSMContext:
    """Minimal stand-in for aiogram's FSMContext, backed by a plain dict instead of a real
    storage backend — handlers only ever call get_data/update_data/set_state/get_state/clear."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._state: Any = None

    async def get_data(self) -> dict[str, Any]:
        return dict(self._data)

    async def update_data(self, **kwargs: Any) -> dict[str, Any]:
        self._data.update(kwargs)
        return dict(self._data)

    async def set_data(self, data: dict[str, Any]) -> None:
        self._data = dict(data)

    async def set_state(self, state: Any) -> None:
        self._state = state

    async def get_state(self) -> Any:
        return self._state

    async def clear(self) -> None:
        self._data = {}
        self._state = None


class Recorder:
    """Records every `.answer(...)` call a fake Message/CallbackQuery.message receives, so a
    test can assert on what the user would have seen without a real Bot/Telegram API."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def answer(self, text: str, reply_markup: Any = None, **kwargs: Any) -> "FakeMessage":
        self.calls.append({"text": text, "reply_markup": reply_markup, **kwargs})
        return make_message(text=text)

    @property
    def texts(self) -> list[str]:
        return [c["text"] for c in self.calls]


class FakeMessage(Recorder):
    def __init__(self, text: str | None, user_id: int, username: str | None, first_name: str | None, chat_id: int) -> None:
        super().__init__()
        self.text = text
        self.from_user = SimpleNamespace(id=user_id, username=username, first_name=first_name)
        self.chat = SimpleNamespace(id=chat_id)


class FakeCallbackQuery(Recorder):
    def __init__(self, data: str, user_id: int, username: str | None, first_name: str | None, chat_id: int) -> None:
        super().__init__()
        self.data = data
        self.from_user = SimpleNamespace(id=user_id, username=username, first_name=first_name)
        self.message = FakeMessage(text=None, user_id=user_id, username=username, first_name=first_name, chat_id=chat_id)
        # handlers/workouts.py's _user_args() branches on `isinstance(x, CallbackQuery)` to decide
        # between `.chat.id` and `.message.chat.id` — a fake can't pass a real aiogram isinstance
        # check, so expose `.chat` directly too (aliased to the same chat as `.message.chat`) and
        # either branch resolves to the same chat id.
        self.chat = self.message.chat

    async def answer(self, *args: Any, **kwargs: Any) -> None:
        # CallbackQuery.answer() just closes Telegram's "loading" spinner on the tap — it's not
        # the same as Message.answer() (sending a reply) and handlers never inspect its result.
        return None


def make_message(
    text: str | None = "hello", *, user_id: int = 1001, username: str | None = "lifter", first_name: str | None = "Bek", chat_id: int = 1001
) -> FakeMessage:
    return FakeMessage(text=text, user_id=user_id, username=username, first_name=first_name, chat_id=chat_id)


def make_callback(
    data: str, *, user_id: int = 1001, username: str | None = "lifter", first_name: str | None = "Bek", chat_id: int = 1001
) -> FakeCallbackQuery:
    return FakeCallbackQuery(data=data, user_id=user_id, username=username, first_name=first_name, chat_id=chat_id)


@pytest.fixture
def state() -> FakeFSMContext:
    return FakeFSMContext()


@pytest.fixture(autouse=True)
def _reset_bot_session_cache():
    """services.session keeps an in-memory {telegram_id: Session} cache at module scope — clear
    it before and after each test so one test's fake session can't leak into the next."""
    from services import session as session_module

    session_module._SESSIONS.clear()
    yield
    session_module._SESSIONS.clear()
