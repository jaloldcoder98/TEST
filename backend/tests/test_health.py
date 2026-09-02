"""Smoke test for Phase 2: the app boots and the health endpoints respond.

More substantial tests (auth, exercises, workouts, ...) land in Phase 8 once those endpoints
exist, but this one is real and running from the start so `pytest` is never a no-op.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"success": True, "status": "ok"}


def test_v1_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["success"] is True
