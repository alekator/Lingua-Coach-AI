from fastapi.testclient import TestClient

from app.main import create_app


def test_health_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "api", "status": "ok"}


def test_scaffold_present() -> None:
    client = TestClient(create_app())
    response = client.get("/_scaffold")

    assert response.status_code == 200
    assert "/chat/*" in response.json()["planned_routes"]
