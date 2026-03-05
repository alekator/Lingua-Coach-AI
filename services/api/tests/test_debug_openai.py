from fastapi.testclient import TestClient

from app.main import create_app


def test_debug_openai_ok() -> None:
    def probe() -> tuple[str, str]:
        return ("ok", "connected")

    client = TestClient(create_app(openai_probe=probe))
    response = client.get("/debug/openai")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "detail": "connected"}


def test_debug_openai_error() -> None:
    def probe() -> tuple[str, str]:
        return ("error", "upstream failed")

    client = TestClient(create_app(openai_probe=probe))
    response = client.get("/debug/openai")

    assert response.status_code == 502
    assert response.json()["detail"] == "upstream failed"
