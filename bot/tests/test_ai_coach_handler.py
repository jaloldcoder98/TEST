"""handlers.ai_coach — the bot's chat state against POST /ai/chat (Phase 7/8). Verifies the menu
button enters the chat state, a normal reply keeps the conversation_id for the next turn, and an
AI_NOT_CONFIGURED backend error is shown as the same honest message the web app uses (and exits
the chat state, since there's nothing useful to keep prompting for)."""

from __future__ import annotations

import handlers.ai_coach as ai_coach
from services.api_client import BackendAPIError
from states import AICoach
from tests.conftest import make_message


async def test_menu_button_enters_chat_state_and_prompts(state):
    message = make_message()
    await ai_coach.ai_coach_menu(message, state)

    assert await state.get_state() == AICoach.chatting
    assert (await state.get_data())["conversation_id"] is None
    assert len(message.calls) == 1


async def test_chat_message_calls_backend_and_stores_conversation_id(state, monkeypatch):
    async def fake_ai_chat(token, text, conversation_id):
        assert token  # a real access token was resolved via call_authed
        assert text == "How should I train legs today?"
        assert conversation_id is None  # first turn
        return {"conversation_id": "conv-123", "context_type": "FITNESS_COACH", "message": "Try squats and lunges."}

    monkeypatch.setattr(ai_coach.backend, "ai_chat", fake_ai_chat)
    monkeypatch.setattr(ai_coach.backend, "telegram_auth", _fake_telegram_auth)

    await state.set_state(AICoach.chatting)
    await state.update_data(conversation_id=None)
    message = make_message(text="How should I train legs today?")

    await ai_coach.ai_coach_message(message, state)

    assert (await state.get_data())["conversation_id"] == "conv-123"
    assert message.texts == ["Try squats and lunges."]


async def test_second_turn_sends_the_stored_conversation_id(state, monkeypatch):
    seen_conversation_ids: list[str | None] = []

    async def fake_ai_chat(token, text, conversation_id):
        seen_conversation_ids.append(conversation_id)
        return {"conversation_id": "conv-123", "context_type": "FITNESS_COACH", "message": "Sure, add some cardio too."}

    monkeypatch.setattr(ai_coach.backend, "ai_chat", fake_ai_chat)
    monkeypatch.setattr(ai_coach.backend, "telegram_auth", _fake_telegram_auth)

    await state.set_state(AICoach.chatting)
    await state.update_data(conversation_id="conv-123")
    message = make_message(text="Anything else?")

    await ai_coach.ai_coach_message(message, state)

    assert seen_conversation_ids == ["conv-123"]


async def test_ai_not_configured_shows_the_honest_message_and_exits_chat_state(state, monkeypatch):
    async def fake_ai_chat(token, text, conversation_id):
        raise BackendAPIError("AI_NOT_CONFIGURED", "no provider configured", 503)

    monkeypatch.setattr(ai_coach.backend, "ai_chat", fake_ai_chat)
    monkeypatch.setattr(ai_coach.backend, "telegram_auth", _fake_telegram_auth)

    await state.set_state(AICoach.chatting)
    await state.update_data(conversation_id=None)
    message = make_message(text="hi")

    await ai_coach.ai_coach_message(message, state)

    assert message.texts == [ai_coach.t("ai_coach.not_ready", "uz")]
    assert await state.get_state() is None  # state.clear() ran


async def test_other_backend_errors_show_the_generic_error_and_stay_in_chat(state, monkeypatch):
    async def fake_ai_chat(token, text, conversation_id):
        raise BackendAPIError("INTERNAL_ERROR", "boom", 500)

    monkeypatch.setattr(ai_coach.backend, "ai_chat", fake_ai_chat)
    monkeypatch.setattr(ai_coach.backend, "telegram_auth", _fake_telegram_auth)

    await state.set_state(AICoach.chatting)
    await state.update_data(conversation_id=None)
    message = make_message(text="hi")

    await ai_coach.ai_coach_message(message, state)

    assert message.texts == [ai_coach.t("common.error", "uz")]
    assert await state.get_state() == AICoach.chatting  # not cleared — a transient error, try again


async def test_blank_message_is_ignored(state, monkeypatch):
    called = False

    async def fake_ai_chat(token, text, conversation_id):
        nonlocal called
        called = True

    monkeypatch.setattr(ai_coach.backend, "ai_chat", fake_ai_chat)

    await state.set_state(AICoach.chatting)
    message = make_message(text="   ")

    await ai_coach.ai_coach_message(message, state)

    assert called is False
    assert message.calls == []


async def _fake_telegram_auth(telegram_id, chat_id, username, first_name, language):
    return {"access_token": "fake-access", "refresh_token": "fake-refresh"}
