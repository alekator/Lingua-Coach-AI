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

    weekly_goal_default = client.get("/progress/weekly-goal", params={"user_id": 901})
    assert weekly_goal_default.status_code == 200
    default_body = weekly_goal_default.json()
    assert default_body["target_minutes"] == 90
    assert default_body["completed_minutes"] >= 8
    assert "completion_percent" in default_body

    client.post("/chat/start", json={"user_id": 901, "mode": "chat"})
    client.post("/chat/start", json={"user_id": 901, "mode": "chat"})
    client.post("/chat/start", json={"user_id": 901, "mode": "chat"})

    weekly_goal_set = client.post(
        "/progress/weekly-goal",
        json={"user_id": 901, "target_minutes": 30},
    )
    assert weekly_goal_set.status_code == 200
    set_body = weekly_goal_set.json()
    assert set_body["target_minutes"] == 30
    assert set_body["remaining_minutes"] >= 0

    rewards = client.get("/progress/rewards", params={"user_id": 901})
    assert rewards.status_code == 200
    rewards_body = rewards.json()
    assert "total_xp" in rewards_body
    assert "items" in rewards_body
    weekly_item_before = next(item for item in rewards_body["items"] if item["id"] == "weekly_goal_complete")
    assert weekly_item_before["status"] == "available"

    claim_weekly = client.post(
        "/progress/rewards/claim",
        json={"user_id": 901, "reward_id": "weekly_goal_complete"},
    )
    assert claim_weekly.status_code == 200
    claim_body = claim_weekly.json()
    weekly_item = next(item for item in claim_body["items"] if item["id"] == "weekly_goal_complete")
    assert weekly_item["status"] == "claimed"

    weekly_review = client.get("/progress/weekly-review", params={"user_id": 901})
    assert weekly_review.status_code == 200
    review_body = weekly_review.json()
    assert review_body["weekly_sessions"] >= 1
    assert review_body["weekly_minutes"] >= 8
    assert "strongest_skill" in review_body
    assert "weakest_skill" in review_body
    assert len(review_body["wins"]) >= 1
    assert "next_focus" in review_body

    outcomes = client.get("/progress/outcomes", params={"user_id": 901})
    assert outcomes.status_code == 200
    outcomes_body = outcomes.json()
    assert outcomes_body["current_level"] in {"A1", "A2", "B1", "B2", "C1", "C2"}
    assert outcomes_body["estimated_level_from_skills"] in {"A1", "A2", "B1", "B2", "C1", "C2"}
    assert "recommendations" in outcomes_body
