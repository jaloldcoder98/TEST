import uuid
from datetime import date

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


def test_log_weight(client, auth_headers) -> None:
    response = client.post("/api/v1/progress/weight", json={"weight_kg": 78.5}, headers=auth_headers)
    assert response.status_code == 200, response.text
    entry = response.json()
    assert entry["weight_kg"] == 78.5
    assert entry["date"] == date.today().isoformat()

    # Logging weight again for the same day updates the existing entry rather than duplicating it.
    response = client.post("/api/v1/progress/weight", json={"weight_kg": 78.0}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["weight_kg"] == 78.0


def test_log_measurements_merges_fields(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/progress/measurements",
        json={"chest_cm": 102.0, "waist_cm": 84.0, "notes": "feeling good"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    entry = response.json()
    assert entry["chest_cm"] == 102.0
    assert entry["waist_cm"] == 84.0
    # weight_kg logged earlier today should be preserved, not wiped out by this partial update.
    assert entry["weight_kg"] == 78.0


def test_progress_summary_includes_weight_and_workout_volume(client, auth_headers, bench_press_id) -> None:
    response = client.post(
        "/api/v1/workouts",
        json={"name": "Progress Test Workout", "exercises": [{"exercise_id": bench_press_id, "order": 0}]},
        headers=auth_headers,
    )
    workout = response.json()
    session = client.post(f"/api/v1/workouts/{workout['id']}/start", headers=auth_headers).json()
    client.post(
        f"/api/v1/workout-sessions/{session['id']}/sets",
        json={"workout_exercise_id": workout["exercises"][0]["id"], "set_number": 1, "reps": 10, "weight_kg": 50.0, "completed": True},
        headers=auth_headers,
    )
    finished = client.post(f"/api/v1/workout-sessions/{session['id']}/finish", headers=auth_headers).json()

    response = client.get("/api/v1/progress", headers=auth_headers)
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["workout_count"] == 1
    assert summary["total_volume_kg"] == finished["total_volume_kg"]
    assert len(summary["volume_trend"]) == 1
    assert any(entry["date"] == date.today().isoformat() and entry["weight_kg"] == 78.0 for entry in summary["weight_trend"])


def test_progress_requires_auth(client) -> None:
    response = client.get("/api/v1/progress")
    assert response.status_code == 401
