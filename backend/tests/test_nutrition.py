import uuid
from datetime import date, timedelta

import pytest


@pytest.fixture(scope="module")
def auth_headers(client):
    username = f"nutrtest_{uuid.uuid4().hex[:12]}"
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_log_food_and_read_today(client, auth_headers) -> None:
    payload = {
        "meal_type": "breakfast",
        "description": "Oatmeal with banana",
        "items": [
            {"name": "Oatmeal", "estimated_grams": 200, "calories": 300, "protein_g": 10, "carbs_g": 50, "fat_g": 5},
            {"name": "Banana", "estimated_grams": 120, "calories": 105, "protein_g": 1, "carbs_g": 27, "fat_g": 0},
        ],
    }
    response = client.post("/api/v1/nutrition/log", json=payload, headers=auth_headers)
    assert response.status_code == 200, response.text
    log = response.json()
    assert log["meal_type"] == "breakfast"
    assert len(log["items"]) == 2
    assert log["total_calories"] == 405
    assert log["date"] == date.today().isoformat()

    response = client.get("/api/v1/nutrition/today", headers=auth_headers)
    assert response.status_code == 200, response.text
    today = response.json()
    assert today["date"] == date.today().isoformat()
    assert today["total_calories"] == 405
    assert today["protein_g"] == 11
    assert len(today["logs"]) == 1
    # No calorie target set on this fresh user's profile -> no target/remaining figures.
    assert today["calorie_target"] is None
    assert today["remaining_calories"] is None


def test_log_food_second_meal_accumulates_daily_totals(client, auth_headers) -> None:
    payload = {
        "meal_type": "lunch",
        "items": [{"name": "Chicken breast", "estimated_grams": 150, "calories": 250, "protein_g": 45, "carbs_g": 0, "fat_g": 6}],
    }
    response = client.post("/api/v1/nutrition/log", json=payload, headers=auth_headers)
    assert response.status_code == 200, response.text

    response = client.get("/api/v1/nutrition/today", headers=auth_headers)
    today = response.json()
    assert today["total_calories"] == 405 + 250
    assert len(today["logs"]) == 2


def test_nutrition_history_range(client, auth_headers) -> None:
    date_from = (date.today() - timedelta(days=7)).isoformat()
    date_to = date.today().isoformat()
    response = client.get("/api/v1/nutrition/history", params={"from": date_from, "to": date_to}, headers=auth_headers)
    assert response.status_code == 200, response.text
    history = response.json()
    assert any(day["date"] == date.today().isoformat() and day["total_calories"] == 655 for day in history)


def test_calorie_target_produces_remaining_calories(client) -> None:
    username = f"nutrtarget_{uuid.uuid4().hex[:10]}"
    token = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch("/api/v1/users/me", json={"daily_calorie_target": 2000}, headers=headers)
    assert response.status_code == 200, response.text

    client.post(
        "/api/v1/nutrition/log",
        json={"meal_type": "dinner", "items": [{"name": "Salmon", "estimated_grams": 200, "calories": 400, "protein_g": 40, "carbs_g": 0, "fat_g": 20}]},
        headers=headers,
    )

    response = client.get("/api/v1/nutrition/today", headers=headers)
    today = response.json()
    assert today["calorie_target"] == 2000
    assert today["remaining_calories"] == 1600


def test_food_log_requires_at_least_one_item(client, auth_headers) -> None:
    response = client.post("/api/v1/nutrition/log", json={"meal_type": "snack", "items": []}, headers=auth_headers)
    assert response.status_code == 422


def test_analyze_image_reports_not_configured(client, auth_headers) -> None:
    response = client.post("/api/v1/nutrition/analyze-image", headers=auth_headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_NOT_CONFIGURED"


def test_nutrition_requires_auth(client) -> None:
    response = client.get("/api/v1/nutrition/today")
    assert response.status_code == 401
