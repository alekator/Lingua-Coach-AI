from __future__ import annotations

from fastapi.testclient import TestClient


def test_e2e_workspace_journey_keeps_progress_isolated(client: TestClient) -> None:
    setup_a = client.post(
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
    assert setup_a.status_code == 200
    user_a = setup_a.json()["user_id"]

    ws_b = client.post(
        "/workspaces",
        json={
            "native_lang": "es",
            "target_lang": "ru",
            "goal": "relocation",
            "make_active": True,
        },
    )
    assert ws_b.status_code == 200
    ws_b_body = ws_b.json()
    ws_b_id = ws_b_body["id"]

    active_b = client.get("/workspaces/active")
    assert active_b.status_code == 200
    user_b = active_b.json()["active_user_id"]
    assert user_b != user_a

    setup_b = client.post(
        "/profile/setup",
        json={
            "user_id": user_b,
            "native_lang": "es",
            "target_lang": "ru",
            "level": "A1",
            "goal": "relocation",
            "preferences": {},
        },
    )
    assert setup_b.status_code == 200
    assert setup_b.json()["user_id"] == user_b

    assert (
        client.post("/vocab/add", json={"user_id": user_a, "word": "airport", "translation": "airport"}).status_code
        == 200
    )
    assert client.post("/vocab/add", json={"user_id": user_a, "word": "hotel", "translation": "hotel"}).status_code == 200
    assert client.post("/vocab/add", json={"user_id": user_b, "word": "gracias", "translation": "thanks"}).status_code == 200

    start_a = client.post("/chat/start", json={"user_id": user_a, "mode": "chat"})
    assert start_a.status_code == 200
    session_a = start_a.json()["session_id"]
    assert client.post("/chat/message", json={"session_id": session_a, "text": "I go airport tomorrow"}).status_code == 200
    assert client.post("/chat/end", json={"session_id": session_a}).status_code == 200

    start_b = client.post("/chat/start", json={"user_id": user_b, "mode": "chat"})
    assert start_b.status_code == 200
    session_b = start_b.json()["session_id"]
    assert client.post("/chat/message", json={"session_id": session_b, "text": "Yo practico ruso cada dia"}).status_code == 200
    assert client.post("/chat/end", json={"session_id": session_b}).status_code == 200

    summary_a = client.get("/progress/summary", params={"user_id": user_a})
    summary_b = client.get("/progress/summary", params={"user_id": user_b})
    assert summary_a.status_code == 200
    assert summary_b.status_code == 200
    assert summary_a.json()["words_learned"] == 2
    assert summary_b.json()["words_learned"] == 1

    journal_a = client.get("/progress/journal", params={"user_id": user_a})
    journal_b = client.get("/progress/journal", params={"user_id": user_b})
    assert journal_a.status_code == 200
    assert journal_b.status_code == 200
    assert journal_a.json()["weekly_sessions"] >= 1
    assert journal_b.json()["weekly_sessions"] >= 1

    switch_b = client.post("/workspaces/switch", json={"workspace_id": ws_b_id})
    assert switch_b.status_code == 200
    bootstrap_b = client.get("/app/bootstrap")
    assert bootstrap_b.status_code == 200
    assert bootstrap_b.json()["user_id"] == user_b
    assert bootstrap_b.json()["active_workspace_id"] == ws_b_id

    all_ws = client.get("/workspaces")
    assert all_ws.status_code == 200
    ws_a_id = next(item["id"] for item in all_ws.json()["items"] if item["target_lang"] == "en")

    switch_a = client.post("/workspaces/switch", json={"workspace_id": ws_a_id})
    assert switch_a.status_code == 200
    bootstrap_a = client.get("/app/bootstrap")
    assert bootstrap_a.status_code == 200
    assert bootstrap_a.json()["user_id"] == user_a
    assert bootstrap_a.json()["active_workspace_id"] == ws_a_id

    summary_a_after = client.get("/progress/summary", params={"user_id": user_a})
    summary_b_after = client.get("/progress/summary", params={"user_id": user_b})
    assert summary_a_after.status_code == 200
    assert summary_b_after.status_code == 200
    assert summary_a_after.json()["words_learned"] == 2
    assert summary_b_after.json()["words_learned"] == 1
