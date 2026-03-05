from fastapi.testclient import TestClient

from app.main import create_app


def test_request_id_header_present() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]


def test_http_exception_has_standard_shape() -> None:
    def probe() -> tuple[str, str]:
        return ("error", "upstream failed")

    client = TestClient(create_app(openai_probe=probe))
    response = client.get("/debug/openai")
    assert response.status_code == 502
    body = response.json()
    assert body["error"] == "http_error"
    assert body["detail"] == "upstream failed"
    assert body["request_id"]


def test_rate_limit_blocks_after_threshold() -> None:
    client = TestClient(create_app(rate_limit_per_minute=2))
    r1 = client.get("/debug/openai")
    r2 = client.get("/debug/openai")
    r3 = client.get("/debug/openai")

    assert r1.status_code in {200, 502}
    assert r2.status_code in {200, 502}
    assert r3.status_code == 429
    body = r3.json()
    assert body["error"] == "rate_limit_exceeded"
