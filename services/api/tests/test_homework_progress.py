from __future__ import annotations

from fastapi.testclient import TestClient


def test_homework_create_list_submit(client: TestClient) -> None:
    created = client.post(
        "/homework/create",
        json={
            "user_id": 900,
            "title": "Past tense practice",
            "tasks": [
                {"id": "t1", "type": "translate", "prompt": "I went home."},
                {"id": "t2", "type": "rewrite", "prompt": "Fix grammar mistakes."},
            ],
        },
    )
    assert created.status_code == 200
    homework_id = created.json()["id"]
    assert created.json()["status"] == "assigned"

    listing = client.get("/homework", params={"user_id": 900})
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == homework_id

    submitted = client.post(
        "/homework/submit",
        json={
            "homework_id": homework_id,
            "answers": {"t1": "Yo fui a casa.", "t2": "I made a mistake."},
        },
    )
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["status"] == "submitted"
    assert body["grade"]["score"] > 0


def test_progress_endpoints(client: TestClient) -> None:
    client.post(
        "/profile/setup",
        json={
            "user_id": 901,
            "native_lang": "ru",
            "target_lang": "en",
            "level": "A2",
            "goal": "work",
            "preferences": {},
        },
    )
    client.post(
        "/vocab/add",
        json={"user_id": 901, "word": "achieve", "translation": "to achieve"},
    )
    client.post("/chat/start", json={"user_id": 901, "mode": "chat"})

    skill_map = client.get("/progress/skill-map", params={"user_id": 901})
    assert skill_map.status_code == 200
    skill_body = skill_map.json()
    assert set(skill_body.keys()) == {"speaking", "listening", "grammar", "vocab", "reading", "writing"}

    streak = client.get("/progress/streak", params={"user_id": 901})
    assert streak.status_code == 200
    assert streak.json()["streak_days"] >= 1

    summary = client.get("/progress/summary", params={"user_id": 901})
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["words_learned"] >= 1
    assert summary_body["minutes_practiced"] >= 8
    assert summary_body["streak_days"] >= 1

    journal = client.get("/progress/journal", params={"user_id": 901})
    assert journal.status_code == 200
    journal_body = journal.json()
    assert "weekly_minutes" in journal_body
    assert "weekly_sessions" in journal_body
    assert "next_actions" in journal_body
    assert len(journal_body["entries"]) >= 1
    assert "session_id" in journal_body["entries"][0]
