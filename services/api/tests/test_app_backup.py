from __future__ import annotations

from fastapi.testclient import TestClient


def test_app_backup_restore_requires_confirmation_token(client: TestClient) -> None:
    export_resp = client.get("/app/backup/export")
    assert export_resp.status_code == 200
    snapshot = export_resp.json()["snapshot"]
    restore = client.post("/app/backup/restore", json={"confirmation": "nope", "snapshot": snapshot})
    assert restore.status_code == 400
    assert restore.json()["detail"] == "Confirmation token must be RESTORE"


def test_app_backup_export_and_restore_full_cycle(client: TestClient) -> None:
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

    workspace_add = client.post(
        "/workspaces",
        json={"native_lang": "es", "target_lang": "fr", "goal": "relocation", "make_active": False},
    )
    assert workspace_add.status_code == 200

    vocab = client.post("/vocab/add", json={"user_id": user_id, "word": "airport", "translation": "airport"})
    assert vocab.status_code == 200

    started = client.post("/chat/start", json={"user_id": user_id, "mode": "chat"})
    assert started.status_code == 200
    session_id = started.json()["session_id"]
    sent = client.post("/chat/message", json={"session_id": session_id, "text": "I go airport tomorrow"})
    assert sent.status_code == 200
    ended = client.post("/chat/end", json={"session_id": session_id})
    assert ended.status_code == 200

    exported = client.get("/app/backup/export")
    assert exported.status_code == 200
    body = exported.json()
    assert body["version"] == 1
    assert "snapshot" in body
    snapshot = body["snapshot"]
    assert len(snapshot["learning_workspaces"]) >= 2
    assert len(snapshot["learner_profiles"]) >= 1
    assert len(snapshot["vocab_items"]) >= 1
    assert len(snapshot["sessions"]) >= 1
    assert len(snapshot["messages"]) >= 1

    reset = client.post("/app/reset", json={"confirmation": "RESET"})
    assert reset.status_code == 200
    bootstrap_after_reset = client.get("/app/bootstrap")
    assert bootstrap_after_reset.status_code == 200
    assert bootstrap_after_reset.json()["needs_onboarding"] is True

    restored = client.post("/app/backup/restore", json={"confirmation": "RESTORE", "snapshot": snapshot})
    assert restored.status_code == 200
    restored_body = restored.json()
    assert restored_body["status"] == "ok"
    assert restored_body["restored_tables"]["learning_workspaces"] >= 2
    assert restored_body["restored_tables"]["learner_profiles"] >= 1

    bootstrap_after_restore = client.get("/app/bootstrap")
    assert bootstrap_after_restore.status_code == 200
    assert bootstrap_after_restore.json()["needs_onboarding"] is False

    workspaces = client.get("/workspaces")
    assert workspaces.status_code == 200
    assert len(workspaces.json()["items"]) >= 2

    profile = client.get("/profile", params={"user_id": user_id})
    assert profile.status_code == 200
    assert profile.json()["target_lang"] == "en"

    vocab_after = client.get("/vocab", params={"user_id": user_id})
    assert vocab_after.status_code == 200
    assert len(vocab_after.json()["items"]) >= 1
