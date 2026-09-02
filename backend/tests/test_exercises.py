import pytest


@pytest.fixture(scope="module")
def auth_headers(client):
    import uuid

    username = f"extest_{uuid.uuid4().hex[:12]}"
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_exercises_default_pagination(client) -> None:
    response = client.get("/api/v1/exercises")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20  # default_page_size — never the full 1323 (spec.md §40)
    assert body["total"] == 1323
    assert len(body["items"]) == 20


def test_list_exercises_filter_by_muscle(client) -> None:
    response = client.get("/api/v1/exercises", params={"muscle": "biceps", "pageSize": 50})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 151  # from docs/ARCHITECTURE.md §1.4
    assert all(item["muscle"] == "biceps" for item in body["items"])


def test_list_exercises_max_page_size_enforced(client) -> None:
    response = client.get("/api/v1/exercises", params={"pageSize": 5000})
    assert response.status_code == 422


def test_search_exercises(client) -> None:
    response = client.get("/api/v1/exercises/search", params={"q": "Barbell Curl"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any("curl" in item["name"].lower() for item in body["items"])


def test_lookup_endpoints(client) -> None:
    for path, expected_count in [
        ("/api/v1/exercises/muscles", 19),
        ("/api/v1/exercises/equipment", 12),
        ("/api/v1/exercises/body-parts", 7),
        ("/api/v1/exercises/categories", 4),
    ]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert len(response.json()) == expected_count, path


def test_exercise_detail_and_not_found(client) -> None:
    listing = client.get("/api/v1/exercises", params={"muscle": "biceps", "pageSize": 1}).json()
    exercise_id = listing["items"][0]["id"]

    response = client.get(f"/api/v1/exercises/{exercise_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == exercise_id
    assert isinstance(body["instructions"], list) and len(body["instructions"]) > 0
    assert body["source"] == "exercisegymgifsdb"

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/exercises/{fake_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EXERCISE_NOT_FOUND"


def test_favorite_and_unfavorite_flow(client, auth_headers) -> None:
    listing = client.get("/api/v1/exercises", params={"muscle": "triceps", "pageSize": 1}).json()
    exercise_id = listing["items"][0]["id"]

    # Not favorited yet
    detail = client.get(f"/api/v1/exercises/{exercise_id}", headers=auth_headers).json()
    assert detail["is_favorited"] is False

    response = client.post(f"/api/v1/exercises/{exercise_id}/favorite", headers=auth_headers)
    assert response.status_code == 200

    detail = client.get(f"/api/v1/exercises/{exercise_id}", headers=auth_headers).json()
    assert detail["is_favorited"] is True

    response = client.delete(f"/api/v1/exercises/{exercise_id}/favorite", headers=auth_headers)
    assert response.status_code == 200

    detail = client.get(f"/api/v1/exercises/{exercise_id}", headers=auth_headers).json()
    assert detail["is_favorited"] is False


def test_favorite_requires_auth(client) -> None:
    listing = client.get("/api/v1/exercises", params={"pageSize": 1}).json()
    exercise_id = listing["items"][0]["id"]
    response = client.post(f"/api/v1/exercises/{exercise_id}/favorite")
    assert response.status_code == 401
