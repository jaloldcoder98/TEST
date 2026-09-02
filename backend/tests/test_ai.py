import re
import uuid

import pytest

import app.services.ai_service as ai_service
from app.ai.providers.base import AIProvider
from app.schemas.ai import AIFoodAnalysisResult, AIGeneratedWorkout, AIWorkoutExercisePick


@pytest.fixture(scope="module")
def auth_headers(client):
    username = f"aitest_{uuid.uuid4().hex[:12]}"
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class _StubProvider(AIProvider):
    """A fake AIProvider for exercising ai_service's own logic (conversation persistence,
    exercise-id grounding) without a real OpenAI key — the thing under test here is
    ai_service's validation, not OpenAI's model quality."""

    def __init__(
        self,
        *,
        chat_reply: str = "Stub reply",
        structured_result=None,
        raise_on_structured: bool = False,
        dynamic_structured=None,
    ):
        self.chat_reply = chat_reply
        self.structured_result = structured_result
        self.raise_on_structured = raise_on_structured
        # Optional callable(user_prompt) -> result, for tests that need to react to whatever
        # candidate exercises the service actually picked for *this* call (the candidate pool is
        # chosen server-side via `ORDER BY random()`, so a test can't know its contents up front).
        self.dynamic_structured = dynamic_structured
        self.chat_calls: list[list[dict]] = []

    async def chat(self, system_prompt: str, history: list[dict]) -> str:
        self.chat_calls.append(history)
        return self.chat_reply

    async def structured(self, system_prompt: str, user_prompt: str, response_model):
        if self.raise_on_structured:
            raise ValueError("stub refusal")
        if self.dynamic_structured is not None:
            return self.dynamic_structured(user_prompt)
        return self.structured_result

    async def analyze_image(self, system_prompt: str, image_url: str, response_model):
        if self.raise_on_structured:
            raise ValueError("stub refusal")
        return self.structured_result


# --- Without a configured provider: every AI route must fail honestly, not fake a response ----


def test_chat_without_provider_returns_503(client, auth_headers) -> None:
    response = client.post("/api/v1/ai/chat", json={"message": "hi"}, headers=auth_headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_NOT_CONFIGURED"


def test_nutrition_chat_without_provider_returns_503(client, auth_headers) -> None:
    response = client.post("/api/v1/ai/nutrition", json={"message": "hi"}, headers=auth_headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_NOT_CONFIGURED"


def test_generate_workout_without_provider_returns_503(client, auth_headers) -> None:
    response = client.post("/api/v1/ai/workout", json={}, headers=auth_headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_NOT_CONFIGURED"


def test_food_analysis_without_provider_returns_503(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/ai/food-analysis", json={"image_url": "https://example.com/meal.jpg"}, headers=auth_headers
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_NOT_CONFIGURED"


def test_ai_endpoints_require_auth(client) -> None:
    assert client.post("/api/v1/ai/chat", json={"message": "hi"}).status_code == 401
    assert client.post("/api/v1/ai/workout", json={}).status_code == 401


# --- With a stub provider: exercise real service-layer logic --------------------------------


def test_chat_persists_conversation_and_reuses_it(client, auth_headers, monkeypatch) -> None:
    stub = _StubProvider(chat_reply="Do more squats.")
    monkeypatch.setattr(ai_service, "get_provider", lambda: stub)

    first = client.post("/api/v1/ai/chat", json={"message": "What should I train today?"}, headers=auth_headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["message"] == "Do more squats."
    conversation_id = body["conversation_id"]

    second = client.post(
        "/api/v1/ai/chat", json={"message": "Anything else?", "conversation_id": conversation_id}, headers=auth_headers
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id
    # The second call's history should include the first turn — proof the conversation persisted.
    assert any(m["content"] == "What should I train today?" for m in stub.chat_calls[-1])


def test_chat_rejects_another_users_conversation_id(client, monkeypatch) -> None:
    stub = _StubProvider()
    monkeypatch.setattr(ai_service, "get_provider", lambda: stub)

    user_a = f"aiconv_a_{uuid.uuid4().hex[:8]}"
    user_b = f"aiconv_b_{uuid.uuid4().hex[:8]}"
    token_a = client.post("/api/v1/auth/register", json={"username": user_a, "password": "password123"}).json()["access_token"]
    token_b = client.post("/api/v1/auth/register", json={"username": user_b, "password": "password123"}).json()["access_token"]

    started = client.post("/api/v1/ai/chat", json={"message": "hi"}, headers={"Authorization": f"Bearer {token_a}"})
    conversation_id = started.json()["conversation_id"]

    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "hi", "conversation_id": conversation_id},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 403


def test_generate_workout_drops_ids_outside_candidate_list(client, auth_headers, monkeypatch) -> None:
    # The candidate pool is chosen server-side (`ORDER BY random() LIMIT 40`), so instead of
    # guessing which exercises will be offered, pull a real id straight out of the candidate list
    # the service actually built for this call (it's listed in the user prompt as "id: <uuid> |
    # ...") and mix it with one that was never offered.
    def build_result(user_prompt: str) -> AIGeneratedWorkout:
        real_id = re.search(r"- id: ([0-9a-fA-F-]{36}) \|", user_prompt).group(1)
        return AIGeneratedWorkout(
            name="Push Day",
            exercises=[
                AIWorkoutExercisePick(exercise_id=real_id, sets=3, reps="8-10", notes="Controlled tempo"),
                AIWorkoutExercisePick(exercise_id=str(uuid.uuid4()), sets=3, reps="8-10", notes="This id was never offered"),
            ],
            notes="Rest 90s between sets.",
        )

    stub = _StubProvider(dynamic_structured=build_result)
    monkeypatch.setattr(ai_service, "get_provider", lambda: stub)

    response = client.post("/api/v1/ai/workout", json={}, headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    # Only the real, offered exercise id survives — the invented one is silently dropped, never
    # trusted, regardless of what the (stubbed) model returned.
    assert len(body["exercises"]) == 1


def test_generate_workout_rejects_when_no_valid_exercises_survive(client, auth_headers, monkeypatch) -> None:
    fake_result = AIGeneratedWorkout(
        name="Push Day",
        exercises=[AIWorkoutExercisePick(exercise_id=str(uuid.uuid4()), sets=3, reps="8-10")],
    )
    stub = _StubProvider(structured_result=fake_result)
    monkeypatch.setattr(ai_service, "get_provider", lambda: stub)

    response = client.post("/api/v1/ai/workout", json={}, headers=auth_headers)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_INVALID_OUTPUT"


def test_generate_workout_refusal_returns_502(client, auth_headers, monkeypatch) -> None:
    stub = _StubProvider(raise_on_structured=True)
    monkeypatch.setattr(ai_service, "get_provider", lambda: stub)

    response = client.post("/api/v1/ai/workout", json={}, headers=auth_headers)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_INVALID_OUTPUT"


def test_food_analysis_with_stub_provider(client, auth_headers, monkeypatch) -> None:
    fake_result = AIFoodAnalysisResult(
        items=[
            {
                "name": "Grilled chicken breast",
                "estimated_grams": 150,
                "calories": 250,
                "protein_g": 45,
                "carbs_g": 0,
                "fat_g": 6,
                "confidence": 0.8,
            }
        ]
    )
    stub = _StubProvider(structured_result=fake_result)
    monkeypatch.setattr(ai_service, "get_provider", lambda: stub)

    response = client.post(
        "/api/v1/ai/food-analysis", json={"image_url": "https://example.com/meal.jpg"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["name"] == "Grilled chicken breast"
