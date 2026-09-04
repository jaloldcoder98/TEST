import uuid

import pytest

from tests.conftest import make_init_data, new_telegram_id


@pytest.fixture(scope="module")
def auth_headers(client):
    """A signed-in user. Telegram is the only door now (D-10), so tests come in
    through it too — a fixture that authenticated some other way would be testing a
    path the product does not have."""
    response = client.post(
        "/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(new_telegram_id())}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def bench_press_id(client):
    body = client.get("/api/v1/exercises", params={"muscle": "pectorals", "pageSize": 1}).json()
    return body["items"][0]["id"]


def test_workout_crud_and_session_flow(client, auth_headers, bench_press_id) -> None:
    # Create
    response = client.post(
        "/api/v1/workouts",
        json={"name": "Push Day", "description": "Chest/shoulders/triceps", "exercises": [{"exercise_id": bench_press_id, "order": 0}]},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    workout = response.json()
    assert workout["name"] == "Push Day"
    assert len(workout["exercises"]) == 1
    workout_id = workout["id"]
    workout_exercise_id = workout["exercises"][0]["id"]

    # List
    response = client.get("/api/v1/workouts", headers=auth_headers)
    assert response.status_code == 200
    assert any(w["id"] == workout_id for w in response.json())

    # Get
    response = client.get(f"/api/v1/workouts/{workout_id}", headers=auth_headers)
    assert response.status_code == 200

    # Update
    response = client.patch(f"/api/v1/workouts/{workout_id}", json={"name": "Push Day A"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Push Day A"

    # Start session
    response = client.post(f"/api/v1/workouts/{workout_id}/start", headers=auth_headers)
    assert response.status_code == 200, response.text
    session = response.json()
    assert session["status"] == "in_progress"
    session_id = session["id"]

    # Log two sets
    for set_number, (reps, weight) in enumerate([(10, 60.0), (8, 65.0)], start=1):
        response = client.post(
            f"/api/v1/workout-sessions/{session_id}/sets",
            json={
                "workout_exercise_id": workout_exercise_id,
                "set_number": set_number,
                "reps": reps,
                "weight_kg": weight,
                "completed": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text

    # Finish
    response = client.post(f"/api/v1/workout-sessions/{session_id}/finish", headers=auth_headers)
    assert response.status_code == 200, response.text
    finished = response.json()
    assert finished["status"] == "completed"
    assert finished["total_sets"] == 2
    assert finished["total_reps"] == 18
    assert finished["total_volume_kg"] == 10 * 60.0 + 8 * 65.0
    assert finished["estimated_calories"] > 0

    # A workout with logged session history can't be deleted (would break history / violate
    # the FK from workout_sets) — it's rejected cleanly, not a raw DB error.
    response = client.delete(f"/api/v1/workouts/{workout_id}", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "WORKOUT_HAS_HISTORY"

    # A workout with no session history deletes fine.
    response = client.post("/api/v1/workouts", json={"name": "Unused", "exercises": []}, headers=auth_headers)
    unused_id = response.json()["id"]
    response = client.delete(f"/api/v1/workouts/{unused_id}", headers=auth_headers)
    assert response.status_code == 200
    response = client.get(f"/api/v1/workouts/{unused_id}", headers=auth_headers)
    assert response.status_code == 404


def test_cannot_access_another_users_workout(client, bench_press_id) -> None:
    user_a = f"wka_{uuid.uuid4().hex[:10]}"
    user_b = f"wkb_{uuid.uuid4().hex[:10]}"
    token_a = client.post("/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(new_telegram_id())}).json()["access_token"]
    token_b = client.post("/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(new_telegram_id())}).json()["access_token"]

    response = client.post(
        "/api/v1/workouts", json={"name": "A's workout", "exercises": []}, headers={"Authorization": f"Bearer {token_a}"}
    )
    workout_id = response.json()["id"]

    response = client.get(f"/api/v1/workouts/{workout_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
