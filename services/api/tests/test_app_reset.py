from __future__ import annotations

import os

from fastapi.testclient import TestClient


def test_app_reset_requires_confirmation_token(client: TestClient) -> None:
    response = client.post("/app/reset", json={"confirmation": "delete"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Confirmation token must be RESET"


def test_app_reset_clears_all_user_data_and_returns_to_first_run(client: TestClient) -> None:
    os.environ["OPENAI_API_KEY"] = "sk-test-reset-123456"

    setup = client.post(
        "/profile/setup",
        json={
            "user_id": 1,
            "native_lang": "de",
            "target_lang": "en",
            "level": "A2",
            "goal": "travel",
            "preferences": {},
        },
    )
    assert setup.status_code == 200
    user_id = setup.json()["user_id"]
    assert user_id != 1

    assert client.post("/vocab/add", json={"user_id": user_id, "word": "airport", "translation": "airport"}).status_code == 200
    started = client.post("/chat/start", json={"user_id": user_id, "mode": "chat"})
    assert started.status_code == 200
    session_id = started.json()["session_id"]
    assert client.post("/chat/message", json={"session_id": session_id, "text": "I go airport tomorrow"}).status_code == 200
    assert client.post("/chat/end", json={"session_id": session_id}).status_code == 200

    reset = client.post("/app/reset", json={"confirmation": "RESET"})
    assert reset.status_code == 200
    body = reset.json()
    assert body["status"] == "ok"
    assert body["deleted_users"] >= 2
    assert body["deleted_workspaces"] >= 1
    assert body["deleted_profiles"] >= 1
    assert body["deleted_vocab_items"] >= 1
    assert body["deleted_chat_sessions"] >= 1
    assert body["openai_key_cleared"] is True

    bootstrap = client.get("/app/bootstrap")
    assert bootstrap.status_code == 200
    bootstrap_body = bootstrap.json()
    assert bootstrap_body["user_id"] == 1
    assert bootstrap_body["has_profile"] is False
    assert bootstrap_body["needs_onboarding"] is True
    assert bootstrap_body["active_workspace_id"] is None

    workspaces = client.get("/workspaces")
    assert workspaces.status_code == 200
    assert workspaces.json()["items"] == []
    assert workspaces.json()["active_workspace_id"] is None

    key_status = client.get("/settings/openai-key")
    assert key_status.status_code == 200
    assert key_status.json()["configured"] is False
    assert "OPENAI_API_KEY" not in os.environ
