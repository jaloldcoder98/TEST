"""handlers.workouts: the /newworkout draft-building FSM and the session-tracking (reps -> weight
-> log set) FSM. These hold real business logic (deduping exercises added twice, refusing to
finish with an empty draft, advancing set numbers) worth testing without a live backend."""

from __future__ import annotations

import handlers.workouts as workouts
from services.api_client import BackendAPIError
from states import NewWorkout, WorkoutSessionFlow
from tests.conftest import make_callback, make_message


async def _fake_telegram_auth(telegram_id, chat_id, username, first_name, language):
    return {"access_token": "fake-access", "refresh_token": "fake-refresh"}


# --- Building a new workout ---------------------------------------------------------------


async def test_new_workout_command_prompts_for_a_name(state):
    message = make_message()
    await workouts.start_new_workout(message, state)
    assert await state.get_state() == NewWorkout.name
    assert message.texts == [workouts.t("workout.new_name_prompt", "uz")]


async def test_receive_workout_name_starts_an_empty_draft_and_moves_to_search(state):
    message = make_message(text="  Push Day  ")
    await workouts.receive_workout_name(message, state)

    data = await state.get_data()
    assert data["name"] == "Push Day"
    assert data["draft"] == []
    assert await state.get_state() == NewWorkout.searching


async def test_add_exercise_to_draft_appends_from_last_search_results(state):
    await state.update_data(draft=[], last_results={"ex-1": "Bench Press"})
    callback = make_callback("addex:ex-1")

    await workouts.add_exercise_to_draft(callback, state)

    data = await state.get_data()
    assert data["draft"] == [{"exercise_id": "ex-1", "name": "Bench Press"}]
    assert callback.message.texts == [workouts.t("workout.new_added", "uz", name="Bench Press")]


async def test_add_exercise_to_draft_does_not_duplicate_the_same_exercise(state):
    await state.update_data(draft=[{"exercise_id": "ex-1", "name": "Bench Press"}], last_results={"ex-1": "Bench Press"})
    callback = make_callback("addex:ex-1")

    await workouts.add_exercise_to_draft(callback, state)

    data = await state.get_data()
    assert data["draft"] == [{"exercise_id": "ex-1", "name": "Bench Press"}]  # still just one


async def test_finish_new_workout_without_any_exercise_refuses(state):
    await state.set_state(NewWorkout.searching)
    await state.update_data(name="Push Day", draft=[])
    message = make_message()

    await workouts.finish_new_workout(message, state)

    assert message.texts == [workouts.t("workout.new_needs_exercise", "uz")]
    assert await state.get_state() == NewWorkout.searching  # state.clear() was NOT called — user can keep adding


async def test_finish_new_workout_creates_the_workout_and_clears_state(state, monkeypatch):
    created_payloads = []

    async def fake_create_workout(token, payload):
        created_payloads.append(payload)
        return {"id": "w-1", "name": payload["name"]}

    monkeypatch.setattr(workouts.backend, "create_workout", fake_create_workout)
    monkeypatch.setattr(workouts.backend, "telegram_auth", _fake_telegram_auth)

    await state.update_data(name="Push Day", draft=[{"exercise_id": "ex-1", "name": "Bench Press"}])
    message = make_message()

    await workouts.finish_new_workout(message, state)

    assert created_payloads == [{"name": "Push Day", "exercises": [{"exercise_id": "ex-1", "order": 0}]}]
    assert await state.get_state() is None
    assert message.texts == [workouts.t("workout.new_created", "uz", name="Push Day", count=1)]


async def test_finish_new_workout_clears_state_even_on_backend_failure(state, monkeypatch):
    async def fake_create_workout(token, payload):
        raise BackendAPIError("VALIDATION_ERROR", "bad payload", 422)

    monkeypatch.setattr(workouts.backend, "create_workout", fake_create_workout)
    monkeypatch.setattr(workouts.backend, "telegram_auth", _fake_telegram_auth)

    await state.update_data(name="Push Day", draft=[{"exercise_id": "ex-1", "name": "Bench Press"}])
    message = make_message()

    await workouts.finish_new_workout(message, state)

    assert await state.get_state() is None
    assert message.texts == [workouts.t("common.error", "uz")]


# --- Session tracking: reps/weight input ----------------------------------------------------


async def test_receive_reps_rejects_non_integer_input(state):
    message = make_message(text="not a number")
    await workouts.receive_reps(message, state)
    assert message.texts == [workouts.t("invalid_number", "uz")]
    assert await state.get_state() is None


async def test_receive_reps_stores_value_and_asks_for_weight(state):
    message = make_message(text="10")
    await workouts.receive_reps(message, state)
    assert (await state.get_data())["pending_reps"] == 10
    assert await state.get_state() == WorkoutSessionFlow.awaiting_weight


async def test_receive_weight_logs_the_set_and_shows_controls(state, monkeypatch):
    logged = []

    async def fake_log_set(token, session_id, payload):
        logged.append((session_id, payload))
        return {"id": "set-1"}

    monkeypatch.setattr(workouts.backend, "log_set", fake_log_set)
    monkeypatch.setattr(workouts.backend, "telegram_auth", _fake_telegram_auth)

    await state.update_data(
        session_id="sess-1",
        exercises=[{"workout_exercise_id": "we-1", "name": "Bench Press"}],
        index=0,
        set_number=1,
        pending_reps=10,
    )
    message = make_message(text="40")

    await workouts.receive_weight(message, state)

    assert logged == [("sess-1", {"workout_exercise_id": "we-1", "set_number": 1, "reps": 10, "weight_kg": 40.0, "completed": True})]
    assert "40.0" in message.texts[0] or "40" in message.texts[0]


async def test_next_exercise_advances_when_more_remain(state):
    await state.update_data(exercises=[{"workout_exercise_id": "we-1", "name": "Bench Press"}, {"workout_exercise_id": "we-2", "name": "Squat"}], index=0, set_number=3)
    callback = make_callback("sess:next")

    await workouts.next_exercise(callback, state)

    data = await state.get_data()
    assert data["index"] == 1
    assert data["set_number"] == 1
    assert await state.get_state() == WorkoutSessionFlow.awaiting_reps
    assert callback.message.texts == [workouts.t("session.next_prompt", "uz", exercise="Squat", set_number=1)]


async def test_next_exercise_announces_completion_when_none_remain(state):
    await state.update_data(exercises=[{"workout_exercise_id": "we-1", "name": "Bench Press"}], index=0, set_number=2)
    callback = make_callback("sess:next")

    await workouts.next_exercise(callback, state)

    assert callback.message.texts == [workouts.t("session.all_exercises_done", "uz")]


async def test_finish_session_clears_state_and_shows_summary(state, monkeypatch):
    async def fake_finish_session(token, session_id):
        assert session_id == "sess-1"
        return {"total_volume_kg": 400, "total_sets": 6, "total_reps": 60, "estimated_calories": 120}

    monkeypatch.setattr(workouts.backend, "finish_session", fake_finish_session)
    monkeypatch.setattr(workouts.backend, "telegram_auth", _fake_telegram_auth)

    await state.update_data(session_id="sess-1")
    callback = make_callback("sess:finish")

    await workouts.finish_session(callback, state)

    assert await state.get_state() is None
    assert callback.message.texts == [
        workouts.t("session.finished", "uz", volume=400, sets=6, reps=60, calories=120)
    ]
