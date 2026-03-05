from fastapi.testclient import TestClient


def test_profile_setup_creates_and_updates_profile(client: TestClient) -> None:
    first = client.post(
        "/profile/setup",
        json={
            "user_id": 101,
            "native_lang": "ru",
            "target_lang": "en",
            "level": "A2",
            "goal": "travel",
            "preferences": {"strictness": "medium"},
        },
    )
    assert first.status_code == 200
    assert first.json()["level"] == "A2"

    second = client.post(
        "/profile/setup",
        json={
            "user_id": 101,
            "native_lang": "ru",
            "target_lang": "en",
            "level": "B1",
            "goal": "interview",
            "preferences": {"strictness": "high"},
        },
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["user_id"] == 101
    assert payload["level"] == "B1"
    assert payload["goal"] == "interview"
    assert payload["preferences"]["strictness"] == "high"


def test_profile_get_returns_saved_profile(client: TestClient) -> None:
    created = client.post(
        "/profile/setup",
        json={
            "user_id": 303,
            "native_lang": "ru",
            "target_lang": "en",
            "level": "B1",
            "goal": "work",
            "preferences": {"strictness": "high"},
        },
    )
    assert created.status_code == 200

    response = client.get("/profile", params={"user_id": 303})
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == 303
    assert payload["native_lang"] == "ru"
    assert payload["target_lang"] == "en"
    assert payload["level"] == "B1"
    assert payload["goal"] == "work"
    assert payload["preferences"]["strictness"] == "high"


def test_profile_get_404_when_missing(client: TestClient) -> None:
    response = client.get("/profile", params={"user_id": 9999})
    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


def test_placement_flow_end_to_end(client: TestClient) -> None:
    started = client.post(
        "/profile/placement-test/start",
        json={"user_id": 202, "native_lang": "ru", "target_lang": "en"},
    )
    assert started.status_code == 200
    start_data = started.json()
    session_id = start_data["session_id"]
    total = start_data["total_questions"]
    assert total >= 3
    assert start_data["question_index"] == 0

    for i in range(total):
        answer = client.post(
            "/profile/placement-test/answer",
            json={
                "session_id": session_id,
                "answer": "This is a sufficiently long answer with multiple words for scoring.",
            },
        )
        assert answer.status_code == 200
        answer_payload = answer.json()
        assert answer_payload["accepted_question_index"] == i
        if i < total - 1:
            assert answer_payload["done"] is False
            assert answer_payload["next_question_index"] == i + 1
        else:
            assert answer_payload["done"] is True
            assert answer_payload["next_question"] is None

    finished = client.post("/profile/placement-test/finish", json={"session_id": session_id})
    assert finished.status_code == 200
    finish_data = finished.json()
    assert finish_data["session_id"] == session_id
    assert finish_data["level"] in {"A1", "A2", "B1", "B2", "C1", "C2"}
    assert 0 <= finish_data["avg_score"] <= 1
    assert set(finish_data["skill_map"].keys()) == {
        "speaking",
        "listening",
        "grammar",
        "vocab",
        "reading",
        "writing",
    }
