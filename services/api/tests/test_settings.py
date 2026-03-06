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


def test_usage_budget_get_and_set(client: TestClient) -> None:
    setup = client.post(
        "/profile/setup",
        json={
            "user_id": 41,
            "native_lang": "de",
            "target_lang": "en",
            "level": "A2",
            "goal": "travel",
            "preferences": {},
        },
    )
    assert setup.status_code == 200

    status_before = client.get("/settings/usage-budget", params={"user_id": 41})
    assert status_before.status_code == 200
    assert status_before.json()["daily_token_cap"] == 12000
    assert status_before.json()["weekly_token_cap"] == 60000

    updated = client.post(
        "/settings/usage-budget",
        json={
            "user_id": 41,
            "daily_token_cap": 9000,
            "weekly_token_cap": 45000,
            "warning_threshold": 0.85,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["daily_token_cap"] == 9000
    assert updated.json()["weekly_token_cap"] == 45000
    assert updated.json()["warning_threshold"] == 0.85

    status_after = client.get("/settings/usage-budget", params={"user_id": 41})
    assert status_after.status_code == 200
    assert status_after.json()["daily_token_cap"] == 9000


def test_language_capabilities_endpoint(client: TestClient) -> None:
    ok = client.get(
        "/settings/language-capabilities",
        params={"native_lang": "de", "target_lang": "en"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["native_lang"] == "de"
    assert body["target_lang"] == "en"
    assert body["text_supported"] is True
    assert "recommendation" in body

    bad = client.get(
        "/settings/language-capabilities",
        params={"native_lang": "en", "target_lang": "en"},
    )
    assert bad.status_code == 400
    assert bad.json()["detail"] == "Native and target language must be different"
