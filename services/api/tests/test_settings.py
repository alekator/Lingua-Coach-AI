from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_openai_key_set_and_status(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(create_app())

    status_before = client.get("/settings/openai-key")
    assert status_before.status_code == 200
    assert status_before.json()["configured"] is False

    set_resp = client.post("/settings/openai-key", json={"api_key": "sk-test-1234567890"})
    assert set_resp.status_code == 200
    assert set_resp.json()["configured"] is True
    assert set_resp.json()["masked"].startswith("sk-t")

    status_after = client.get("/settings/openai-key")
    assert status_after.status_code == 200
    assert status_after.json()["configured"] is True
    assert status_after.json()["source"] == "env"
