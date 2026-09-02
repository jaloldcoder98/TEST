"""Smoke test: the app boots and the health endpoints respond."""


def test_root_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"success": True, "status": "ok"}


def test_v1_health(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["success"] is True
