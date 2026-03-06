from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from app.schemas.chat import ChatMessageResponse, Correction


def test_translate_voice_pipeline(client_factory: Callable[..., TestClient]) -> None:
    def fake_asr(audio: bytes, filename: str, content_type: str, language_hint: str) -> dict[str, str]:
        return {"transcript": "hello", "language": "en"}

    def fake_translator(text: str, source_lang: str, target_lang: str) -> str:
        return "hola"

    def fake_tts(text: str, target_lang: str, voice_name: str) -> str:
        return "http://tts.local/audio/x.mp3"

    with client_factory(
        asr_transcriber=fake_asr,
        translator=fake_translator,
        tts_synthesizer=fake_tts,
    ) as client:
        response = client.post(
            "/translate/voice",
            files={"file": ("sample.webm", b"abc", "audio/webm")},
            data={"source_lang": "en", "target_lang": "es", "language_hint": "en"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["transcript"] == "hello"
        assert body["translated_text"] == "hola"
        assert body["audio_url"] == "http://tts.local/audio/x.mp3"


def test_grammar_analyze(client: TestClient) -> None:
    response = client.post(
        "/grammar/analyze",
        json={"user_id": 1, "text": "I goed to school", "target_lang": "en"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "I went to school" in body["corrected_text"]
    assert len(body["exercises"]) >= 1

    history = client.get("/grammar/history", params={"user_id": 1, "limit": 10})
    assert history.status_code == 200
    history_items = history.json()["items"]
    assert len(history_items) >= 1
    assert history_items[0]["input_text"] == "I goed to school"
    assert "corrected_text" in history_items[0]


def test_exercises_generate_and_grade(client: TestClient) -> None:
    generated = client.post(
        "/exercises/generate",
        json={"user_id": 1, "exercise_type": "fill_blank", "topic": "travel", "count": 3},
    )
    assert generated.status_code == 200
    items = generated.json()["items"]
    assert len(items) == 3

    expected = {item["id"]: item["expected_answer"] for item in items}
    answers = {items[0]["id"]: items[0]["expected_answer"], items[1]["id"]: "wrong", items[2]["id"]: "wrong"}
    graded = client.post("/exercises/grade", json={"answers": answers, "expected": expected})
    assert graded.status_code == 200
    body = graded.json()
    assert body["score"] == 1.0
    assert body["max_score"] == 3.0
    assert "rubric" in body
    assert "ex-1" in body["rubric"]
    assert body["rubric"]["ex-1"]["is_correct"] is True
    assert "item_score" in body["rubric"]["ex-2"]


def test_plan_today_and_scenarios(client_factory: Callable[..., TestClient]) -> None:
    def fake_teacher(_: dict[str, Any]) -> ChatMessageResponse:
        return ChatMessageResponse(
            assistant_text="Nice try. One correction.",
            corrections=[
                Correction(
                    type="grammar",
                    bad="I did a mistake",
                    good="I made a mistake",
                    explanation="Use 'make a mistake'",
                )
            ],
            new_words=[],
            homework_suggestions=[],
        )

    with client_factory(teacher_responder=fake_teacher) as client:
        setup = client.post(
            "/profile/setup",
            json={
                "user_id": 1,
                "native_lang": "ru",
                "target_lang": "en",
                "level": "A2",
                "goal": "interview",
                "preferences": {},
            },
        )
        assert setup.status_code == 200
        workspace_user_id = setup.json()["user_id"]
        assert workspace_user_id != 1

        # Make one due SRS card and one tracked grammar mistake to drive adaptation.
        vocab = client.post(
            "/vocab/add",
            json={"user_id": workspace_user_id, "word": "achieve", "translation": "to achieve"},
        )
        assert vocab.status_code == 200

        started = client.post("/chat/start", json={"user_id": workspace_user_id, "mode": "chat"})
        session_id = started.json()["session_id"]
        msg = client.post("/chat/message", json={"session_id": session_id, "text": "I did a mistake"})
        assert msg.status_code == 200

        plan = client.get("/plan/today", params={"user_id": workspace_user_id, "time_budget_minutes": 20})
        assert plan.status_code == 200
        plan_body = plan.json()
        assert plan_body["user_id"] == workspace_user_id
        assert plan_body["time_budget_minutes"] == 20
        assert len(plan_body["tasks"]) == 3
        assert len(plan_body["adaptation_notes"]) >= 1
        assert "interview" in plan_body["focus"]
        assert "grammar" in plan_body["focus"]
        assert "vocab" in plan_body["focus"]
        assert "due cards:" in plan_body["tasks"][0]
        assert "targeted correction drill (grammar)" in plan_body["tasks"][1]
        assert any("Low recent consistency detected" in note for note in plan_body["adaptation_notes"])

        session = client.get("/coach/session/today", params={"user_id": workspace_user_id, "time_budget_minutes": 20})
        assert session.status_code == 200
        session_body = session.json()
        assert session_body["time_budget_minutes"] == 20
        assert len(session_body["steps"]) == 5
        assert session_body["steps"][0]["id"] == "warmup"
        assert session_body["steps"][-1]["id"] == "recap"
        assert session_body["steps"][1]["route"] == "/app/chat"

        next_actions = client.get("/coach/next-actions", params={"user_id": workspace_user_id})
        assert next_actions.status_code == 200
        next_body = next_actions.json()
        assert next_body["user_id"] == workspace_user_id
        assert len(next_body["items"]) >= 1
        assert "title" in next_body["items"][0]
        assert "route" in next_body["items"][0]

        daily_challenge = client.get("/coach/daily-challenge", params={"user_id": workspace_user_id})
        assert daily_challenge.status_code == 200
        challenge_body = daily_challenge.json()
        assert challenge_body["user_id"] == workspace_user_id
        assert challenge_body["estimated_minutes"] == 5
        assert "title" in challenge_body
        assert challenge_body["route"] in {"/app/vocab", "/app/chat"}

        trajectory = client.get("/coach/trajectory", params={"user_id": workspace_user_id, "horizon_days": 90})
        assert trajectory.status_code == 200
        trajectory_body = trajectory.json()
        assert trajectory_body["horizon_days"] == 90
        assert trajectory_body["current_phase"] in {"foundation", "consolidation", "expansion"}
        assert len(trajectory_body["milestones"]) >= 4

        roadmap = client.get("/coach/roadmap", params={"user_id": workspace_user_id})
        assert roadmap.status_code == 200
        roadmap_body = roadmap.json()
        assert roadmap_body["goal"] == "interview"
        assert len(roadmap_body["items"]) >= 3
        assert roadmap_body["items"][0]["priority"] == 1

        outcome_packs = client.get("/coach/outcome-packs", params={"user_id": workspace_user_id})
        assert outcome_packs.status_code == 200
        packs_body = outcome_packs.json()
        assert len(packs_body["items"]) >= 3
        assert packs_body["items"][0]["readiness"] in {"ready", "almost_ready", "not_ready"}

        reactivation_recent = client.get(
            "/coach/reactivation",
            params={"user_id": workspace_user_id, "available_minutes": 12},
        )
        assert reactivation_recent.status_code == 200
        recent_body = reactivation_recent.json()
        assert recent_body["eligible"] is False
        assert recent_body["gap_days"] == 0
        assert recent_body["available_minutes"] == 12
        assert recent_body["tasks"] == []

        reactivation_new_user = client.get("/coach/reactivation", params={"user_id": 999, "available_minutes": 7})
        assert reactivation_new_user.status_code == 200
        new_user_body = reactivation_new_user.json()
        assert new_user_body["eligible"] is True
        assert new_user_body["gap_days"] >= 2
        assert new_user_body["available_minutes"] == 7
        assert new_user_body["recommended_minutes"] == 7
        assert new_user_body["plan_mode"] == "micro"
        assert len(new_user_body["tasks"]) == 3
        assert new_user_body["cta_route"] in {"/app/chat", "/app/vocab"}

        scenarios = client.get("/scenarios")
        assert scenarios.status_code == 200
        items = scenarios.json()["items"]
        assert len(items) >= 20
        assert "required_level" in items[0]
        assert "unlocked" in items[0]

        chosen = client.post(
            "/scenarios/select",
            json={"user_id": workspace_user_id, "scenario_id": items[0]["id"]},
        )
        assert chosen.status_code == 200
        assert chosen.json()["mode"].startswith("scenario:")

        script = client.get(
            "/scenarios/script",
            params={"scenario_id": "job-interview", "user_id": workspace_user_id},
        )
        assert script.status_code == 200
        script_body = script.json()
        assert script_body["scenario_id"] == "job-interview"
        assert len(script_body["steps"]) >= 1
        first_step = script_body["steps"][0]
        assert "Use short simple sentences" in first_step["coach_prompt"]

        turn = client.post(
            "/scenarios/turn",
            json={
                "user_id": workspace_user_id,
                "scenario_id": "job-interview",
                "step_id": first_step["id"],
                "user_text": "I have experience in this role and skills",
            },
        )
        assert turn.status_code == 200
        turn_body = turn.json()
        assert turn_body["score"] >= 1
        assert turn_body["max_score"] >= 1
        assert "feedback" in turn_body
        if turn_body["suggested_reply"]:
            assert "Example:" in turn_body["suggested_reply"]


def test_mastery_gate_blocks_locked_scenario_selection(client: TestClient) -> None:
    setup = client.post(
        "/profile/setup",
        json={
            "user_id": 1,
            "native_lang": "ru",
            "target_lang": "en",
            "level": "A1",
            "goal": "job",
            "preferences": {},
        },
    )
    assert setup.status_code == 200
    workspace_user_id = setup.json()["user_id"]

    scenarios = client.get("/scenarios", params={"user_id": workspace_user_id})
    assert scenarios.status_code == 200
    items = scenarios.json()["items"]
    interview = next(item for item in items if item["id"] == "job-interview")
    assert interview["unlocked"] is False
    assert interview["required_level"] in {"B1", "B2", "C1", "C2"}

    selected = client.post(
        "/scenarios/select",
        json={"user_id": workspace_user_id, "scenario_id": "job-interview"},
    )
    assert selected.status_code == 403
    assert "Unlock at" in selected.json()["detail"]


def test_scenario_turn_supports_non_english_target_without_keyword_lock(client: TestClient) -> None:
    setup = client.post(
        "/profile/setup",
        json={
            "user_id": 1,
            "native_lang": "de",
            "target_lang": "ru",
            "level": "B1",
            "goal": "job",
            "preferences": {},
        },
    )
    assert setup.status_code == 200
    workspace_user_id = setup.json()["user_id"]

    script = client.get(
        "/scenarios/script",
        params={"scenario_id": "job-interview", "user_id": workspace_user_id},
    )
    assert script.status_code == 200
    first_step = script.json()["steps"][0]

    turn = client.post(
        "/scenarios/turn",
        json={
            "user_id": workspace_user_id,
            "scenario_id": "job-interview",
            "step_id": first_step["id"],
            "user_text": "У меня есть опыт в этой роли и сильные коммуникативные навыки.",
        },
    )
    assert turn.status_code == 200
    body = turn.json()
    assert body["max_score"] >= 1
    assert body["score"] >= 1
    if body["suggested_reply"]:
        assert "answers the prompt" in body["suggested_reply"]


def test_coach_reactivation_uses_vocab_cta_when_due_cards_exist(client: TestClient) -> None:
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
    workspace_user_id = setup.json()["user_id"]

    vocab = client.post(
        "/vocab/add",
        json={"user_id": workspace_user_id, "word": "airport", "translation": "airport"},
    )
    assert vocab.status_code == 200

    reactivation = client.get("/coach/reactivation", params={"user_id": workspace_user_id, "available_minutes": 9})
    assert reactivation.status_code == 200
    body = reactivation.json()
    assert body["eligible"] is True
    assert body["available_minutes"] == 9
    assert body["recommended_minutes"] == 9
    assert body["cta_route"] == "/app/vocab"


def test_coach_session_progress_lifecycle(client: TestClient) -> None:
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
    workspace_user_id = setup.json()["user_id"]

    progress = client.get(
        "/coach/session/progress",
        params={"user_id": workspace_user_id, "time_budget_minutes": 15},
    )
    assert progress.status_code == 200
    body = progress.json()
    assert body["user_id"] == workspace_user_id
    assert body["total_steps"] == 5
    assert body["completed_steps"] == 0
    step_id = body["items"][0]["step_id"]
    assert body["items"][0]["status"] == "pending"

    started = client.post(
        "/coach/session/progress",
        json={
            "user_id": workspace_user_id,
            "step_id": step_id,
            "status": "in_progress",
            "time_budget_minutes": 15,
        },
    )
    assert started.status_code == 200
    started_body = started.json()
    first_item = next(item for item in started_body["items"] if item["step_id"] == step_id)
    assert first_item["status"] == "in_progress"
    assert first_item["started_at"] is not None
    assert first_item["completed_at"] is None

    completed = client.post(
        "/coach/session/progress",
        json={
            "user_id": workspace_user_id,
            "step_id": step_id,
            "status": "completed",
            "time_budget_minutes": 15,
        },
    )
    assert completed.status_code == 200
    completed_body = completed.json()
    first_item_done = next(item for item in completed_body["items"] if item["step_id"] == step_id)
    assert first_item_done["status"] == "completed"
    assert first_item_done["completed_at"] is not None
    assert completed_body["completed_steps"] == 1
    assert completed_body["completion_percent"] == 20

    invalid = client.post(
        "/coach/session/progress",
        json={
            "user_id": workspace_user_id,
            "step_id": "nonexistent-step",
            "status": "completed",
            "time_budget_minutes": 15,
        },
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "Invalid step_id for today's session"


def test_coach_error_bank_and_next_actions(client_factory: Callable[..., TestClient]) -> None:
    def fake_teacher(_: dict[str, Any]) -> ChatMessageResponse:
        return ChatMessageResponse(
            assistant_text="Let's fix this pattern.",
            corrections=[
                Correction(
                    type="grammar",
                    bad="I goed home",
                    good="I went home",
                    explanation="Use irregular past form 'went'.",
                ),
                Correction(
                    type="grammar",
                    bad="I goed yesterday",
                    good="I went yesterday",
                    explanation="Past form must be 'went'.",
                ),
            ],
            new_words=[],
            homework_suggestions=[],
        )

    with client_factory(teacher_responder=fake_teacher) as client:
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
        workspace_user_id = setup.json()["user_id"]

        started = client.post("/chat/start", json={"user_id": workspace_user_id, "mode": "chat"})
        assert started.status_code == 200
        session_id = started.json()["session_id"]
        sent = client.post("/chat/message", json={"session_id": session_id, "text": "I goed home"})
        assert sent.status_code == 200

        bank = client.get("/coach/error-bank", params={"user_id": workspace_user_id})
        assert bank.status_code == 200
        body = bank.json()
        assert body["user_id"] == workspace_user_id
        assert len(body["items"]) >= 1
        top = body["items"][0]
        assert top["category"] == "grammar"
        assert top["occurrences"] >= 2
        assert "Rewrite 3 short lines" in top["drill_prompt"]

        next_actions = client.get("/coach/next-actions", params={"user_id": workspace_user_id})
        assert next_actions.status_code == 200
        actions = next_actions.json()["items"]
        error_action = next(item for item in actions if item["id"] == "error-bank-top")
        assert error_action["route"].startswith("/app/exercises?topic=grammar")
        assert error_action["quick_mode_minutes"] == 5


def test_coach_review_queue_combines_vocab_grammar_pronunciation(
    client_factory: Callable[[Callable[[dict[str, Any]], ChatMessageResponse]], TestClient],
) -> None:
    def fake_teacher(_: dict[str, Any]) -> ChatMessageResponse:
        return ChatMessageResponse(
            assistant_text="Queue signal",
            corrections=[
                Correction(type="grammar", bad="I goed", good="I went", explanation="Irregular past"),
                Correction(type="pronunciation", bad="th", good="th", explanation="Stress pattern"),
            ],
            new_words=[],
            homework_suggestions=[],
        )

    with client_factory(fake_teacher) as client:
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
        workspace_user_id = setup.json()["user_id"]

        vocab = client.post(
            "/vocab/add",
            json={"user_id": workspace_user_id, "word": "airport", "translation": "airport"},
        )
        assert vocab.status_code == 200

        started = client.post("/chat/start", json={"user_id": workspace_user_id, "mode": "chat"})
        assert started.status_code == 200
        session_id = started.json()["session_id"]
        message = client.post("/chat/message", json={"session_id": session_id, "text": "I goed to airport"})
        assert message.status_code == 200

        queue = client.get("/coach/review-queue", params={"user_id": workspace_user_id})
        assert queue.status_code == 200
        body = queue.json()
        assert body["user_id"] == workspace_user_id
        assert len(body["items"]) >= 3
        types = {item["type"] for item in body["items"]}
        assert "vocab" in types
        assert "grammar" in types
        assert "pronunciation" in types


def test_coach_scenario_tracks_progress_and_milestones(client: TestClient) -> None:
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

    tracks_before = client.get("/coach/scenario-tracks", params={"user_id": workspace_user_id})
    assert tracks_before.status_code == 200
    before_body = tracks_before.json()
    assert len(before_body["items"]) >= 3
    travel_track = before_body["items"][0]
    assert travel_track["goal"] == "travel"
    assert travel_track["completed_steps"] == 0
    assert travel_track["steps"][0]["status"] == "available"
    assert travel_track["milestones"][0]["is_reached"] is False
    first_scenario_id = travel_track["steps"][0]["scenario_id"]

    warmup_chat = client.post("/chat/start", json={"user_id": workspace_user_id, "mode": "chat"})
    assert warmup_chat.status_code == 200
    warmup_session_id = warmup_chat.json()["session_id"]
    warmup_turn = client.post("/chat/message", json={"session_id": warmup_session_id, "text": "I practice travel english"})
    assert warmup_turn.status_code == 200

    selected = client.post(
        "/scenarios/select",
        json={"user_id": workspace_user_id, "scenario_id": first_scenario_id},
    )
    assert selected.status_code == 200
    session_id = selected.json()["session_id"]
    ended = client.post("/chat/end", json={"session_id": session_id})
    assert ended.status_code == 200

    tracks_after = client.get("/coach/scenario-tracks", params={"user_id": workspace_user_id})
    assert tracks_after.status_code == 200
    after_body = tracks_after.json()
    travel_after = next(item for item in after_body["items"] if item["goal"] == "travel")
    assert travel_after["completed_steps"] >= 1
    assert travel_after["milestones"][0]["is_reached"] is True
