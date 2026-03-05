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
        json={"text": "I goed to school", "target_lang": "en"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "I went to school" in body["corrected_text"]
    assert len(body["exercises"]) >= 1


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

        # Make one due SRS card and one tracked grammar mistake to drive adaptation.
        vocab = client.post(
            "/vocab/add",
            json={"user_id": 1, "word": "achieve", "translation": "to achieve"},
        )
        assert vocab.status_code == 200

        started = client.post("/chat/start", json={"user_id": 1, "mode": "chat"})
        session_id = started.json()["session_id"]
        msg = client.post("/chat/message", json={"session_id": session_id, "text": "I did a mistake"})
        assert msg.status_code == 200

        plan = client.get("/plan/today", params={"user_id": 1, "time_budget_minutes": 20})
        assert plan.status_code == 200
        plan_body = plan.json()
        assert plan_body["user_id"] == 1
        assert plan_body["time_budget_minutes"] == 20
        assert len(plan_body["tasks"]) == 3
        assert len(plan_body["adaptation_notes"]) >= 1
        assert "interview" in plan_body["focus"]
        assert "grammar" in plan_body["focus"]
        assert "vocab" in plan_body["focus"]
        assert "due cards:" in plan_body["tasks"][0]
        assert "targeted correction drill (grammar)" in plan_body["tasks"][1]
        assert "Low recent consistency detected" in plan_body["adaptation_notes"][0]

        session = client.get("/coach/session/today", params={"user_id": 1, "time_budget_minutes": 20})
        assert session.status_code == 200
        session_body = session.json()
        assert session_body["time_budget_minutes"] == 20
        assert len(session_body["steps"]) == 5
        assert session_body["steps"][0]["id"] == "warmup"
        assert session_body["steps"][-1]["id"] == "recap"
        assert session_body["steps"][1]["route"] == "/app/chat"

        scenarios = client.get("/scenarios")
        assert scenarios.status_code == 200
        items = scenarios.json()["items"]
        assert len(items) >= 1

        chosen = client.post("/scenarios/select", json={"user_id": 1, "scenario_id": items[0]["id"]})
        assert chosen.status_code == 200
        assert chosen.json()["mode"].startswith("scenario:")

        script = client.get("/scenarios/script", params={"scenario_id": "job-interview"})
        assert script.status_code == 200
        script_body = script.json()
        assert script_body["scenario_id"] == "job-interview"
        assert len(script_body["steps"]) >= 1
        first_step = script_body["steps"][0]

        turn = client.post(
            "/scenarios/turn",
            json={
                "user_id": 1,
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
