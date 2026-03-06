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

    skill_tree = client.get("/progress/skill-tree", params={"user_id": 901})
    assert skill_tree.status_code == 200
    tree_body = skill_tree.json()
    assert tree_body["current_level"] in {"A1", "A2", "B1", "B2", "C1", "C2"}
    assert tree_body["estimated_level_from_skills"] in {"A1", "A2", "B1", "B2", "C1", "C2"}
    assert len(tree_body["items"]) == 6
    assert "closed_criteria" in tree_body["items"][0]
    assert "remaining_criteria" in tree_body["items"][0]

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

    checkpoint = client.get("/progress/weekly-checkpoint", params={"user_id": 901})
    assert checkpoint.status_code == 200
    checkpoint_body = checkpoint.json()
    assert checkpoint_body["window_days"] == 7
    assert "delta_points" in checkpoint_body
    assert "measurable_growth" in checkpoint_body
    assert len(checkpoint_body["skills"]) == 6
    assert "summary" in checkpoint_body

    achievements = client.get("/progress/achievements", params={"user_id": 901})
    assert achievements.status_code == 200
    achievements_body = achievements.json()
    assert len(achievements_body["items"]) >= 3
    assert achievements_body["items"][0]["status"] in {"unlocked", "in_progress"}

    report = client.get("/progress/report", params={"user_id": 901, "period_days": 30})
    assert report.status_code == 200
    report_body = report.json()
    assert report_body["period_days"] == 30
    assert "export_markdown" in report_body
    assert "Highlights" in report_body["export_markdown"]


def test_progress_profile_defaults_follow_workspace_lang_pair(client: TestClient) -> None:
    created = client.post(
        "/workspaces",
        json={"native_lang": "es", "target_lang": "fr", "goal": "relocation", "make_active": True},
    )
    assert created.status_code == 200

    active = client.get("/workspaces/active")
    assert active.status_code == 200
    workspace_user_id = active.json()["active_user_id"]

    weekly_goal_set = client.post(
        "/progress/weekly-goal",
        json={"user_id": workspace_user_id, "target_minutes": 120},
    )
    assert weekly_goal_set.status_code == 200

    profile = client.get("/profile", params={"user_id": workspace_user_id})
    assert profile.status_code == 200
    profile_body = profile.json()
    assert profile_body["native_lang"] == "es"
    assert profile_body["target_lang"] == "fr"


def test_progress_profile_defaults_for_owner_follow_active_workspace(client: TestClient) -> None:
    created = client.post(
        "/workspaces",
        json={"native_lang": "de", "target_lang": "it", "goal": "relocation", "make_active": True},
    )
    assert created.status_code == 200

    weekly_goal_set = client.post(
        "/progress/weekly-goal",
        json={"user_id": 1, "target_minutes": 150},
    )
    assert weekly_goal_set.status_code == 200

    profile = client.get("/profile", params={"user_id": 1})
    assert profile.status_code == 200
    profile_body = profile.json()
    assert profile_body["native_lang"] == "de"
    assert profile_body["target_lang"] == "it"


def test_progress_timeline_with_filters_and_workspace_scope(client: TestClient) -> None:
    setup = client.post(
        "/profile/setup",
        json={
            "user_id": 1,
            "native_lang": "ru",
            "target_lang": "en",
            "level": "A2",
            "goal": "travel",
            "preferences": {},
        },
    )
    assert setup.status_code == 200
    workspace_user_id = setup.json()["user_id"]

    vocab = client.post("/vocab/add", json={"user_id": workspace_user_id, "word": "airport", "translation": "airport"})
    assert vocab.status_code == 200
    next_item = client.post("/vocab/review/next", json={"user_id": workspace_user_id})
    assert next_item.status_code == 200
    item_id = next_item.json()["item"]["id"]
    submit = client.post(
        "/vocab/review/submit",
        json={"user_id": workspace_user_id, "vocab_item_id": item_id, "rating": "good"},
    )
    assert submit.status_code == 200

    started = client.post("/chat/start", json={"user_id": workspace_user_id, "mode": "chat"})
    assert started.status_code == 200
    session_id = started.json()["session_id"]
    message = client.post("/chat/message", json={"session_id": session_id, "text": "I goed to airport"})
    assert message.status_code == 200
    client.post("/chat/end", json={"session_id": session_id})

    homework = client.post(
        "/homework/create",
        json={"user_id": workspace_user_id, "title": "Quick grammar", "tasks": [{"id": "t1", "prompt": "Fix sentence"}]},
    )
    assert homework.status_code == 200
    hw_submit = client.post("/homework/submit", json={"homework_id": homework.json()["id"], "answers": {"t1": "fixed"}})
    assert hw_submit.status_code == 200

    timeline = client.get("/progress/timeline", params={"user_id": workspace_user_id})
    assert timeline.status_code == 200
    body = timeline.json()
    assert len(body["items"]) >= 3

    vocab_only = client.get(
        "/progress/timeline",
        params={"user_id": workspace_user_id, "activity_type": "vocab_review"},
    )
    assert vocab_only.status_code == 200
    assert all(item["activity_type"] == "vocab_review" for item in vocab_only.json()["items"])

    grammar_only = client.get(
        "/progress/timeline",
        params={"user_id": workspace_user_id, "skill": "grammar"},
    )
    assert grammar_only.status_code == 200
    assert all("grammar" in [tag.lower() for tag in item["skill_tags"]] for item in grammar_only.json()["items"])

    workspaces = client.get("/workspaces")
    assert workspaces.status_code == 200
    workspace_id = workspaces.json()["active_workspace_id"]
    scoped = client.get(
        "/progress/timeline",
        params={"user_id": workspace_user_id, "workspace_id": workspace_id},
    )
    assert scoped.status_code == 200
    assert all(item["workspace_id"] == workspace_id for item in scoped.json()["items"])
