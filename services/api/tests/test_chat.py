from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.schemas.chat import ChatMessageResponse, Correction, NewWord
from app.services.teacher import default_teacher_responder


def test_chat_flow_with_memory_updates(
    client_factory: Callable[[Callable[[dict[str, Any]], ChatMessageResponse]], TestClient],
) -> None:
    payloads: list[dict[str, Any]] = []

    def fake_teacher(payload: dict[str, Any]) -> ChatMessageResponse:
        payloads.append(payload)
        return ChatMessageResponse(
            assistant_text="Great effort. Small correction below.",
            corrections=[
                Correction(
                    type="grammar",
                    bad="I did a mistake",
                    good="I made a mistake",
                    explanation="Use 'make a mistake'",
                )
            ],
            new_words=[
                NewWord(
                    word="achieve",
                    translation="to achieve",
                    example="I want to achieve my goals.",
                )
            ],
            homework_suggestions=["Write 5 sentences with 'achieve'."],
            rubric={
                "overall_score": 72,
                "level_band": "developing",
                "grammar_accuracy": {"score": 3, "feedback": "Fix verb + collocation errors."},
                "lexical_range": {"score": 3, "feedback": "Reuse one new word in context."},
                "fluency_coherence": {"score": 4, "feedback": "Ideas are clear and connected."},
                "task_completion": {"score": 4, "feedback": "You completed the prompt intent."},
                "strengths": ["Clear intent"],
                "priority_fixes": ["I did a mistake -> I made a mistake"],
                "next_drill": "Write 3 lines about travel using 'make a mistake' correctly.",
            },
        )

    with client_factory(fake_teacher) as client:
        setup = client.post(
            "/profile/setup",
            json={
                "user_id": 7,
                "native_lang": "ru",
                "target_lang": "en",
                "level": "A2",
                "goal": "travel",
                "preferences": {"strictness": "medium"},
            },
        )
        assert setup.status_code == 200

        started = client.post("/chat/start", json={"user_id": 7, "mode": "chat"})
        assert started.status_code == 200
        session_id = started.json()["session_id"]

        msg1 = client.post("/chat/message", json={"session_id": session_id, "text": "I did a mistake"})
        assert msg1.status_code == 200
        body1 = msg1.json()
        assert body1["assistant_text"]
        assert body1["corrections"][0]["good"] == "I made a mistake"
        assert body1["new_words"][0]["word"] == "achieve"
        assert body1["rubric"]["overall_score"] == 72

        msg2 = client.post("/chat/message", json={"session_id": session_id, "text": "Thanks, understood"})
        assert msg2.status_code == 200
        assert len(payloads) == 2
        assert payloads[0]["learner_profile"]["level"] == "A2"
        assert payloads[1]["history"][0]["role"] == "user"
        assert payloads[1]["history"][1]["role"] == "assistant"
        assert "grammar" in payloads[1]["learner_profile"]["weak_topics"]
        assert payloads[1]["recent_mistakes"][0]["category"] == "grammar"
        assert any(word["word"] == "achieve" for word in payloads[1]["learner_profile"]["active_vocab"])
        assert "rubric" in payloads[0]["schema"]


def test_chat_end_blocks_future_messages(
    client_factory: Callable[[Callable[[dict[str, Any]], ChatMessageResponse]], TestClient],
) -> None:
    def fake_teacher(_: dict[str, Any]) -> ChatMessageResponse:
        return ChatMessageResponse(assistant_text="ok")

    with client_factory(fake_teacher) as client:
        started = client.post("/chat/start", json={"user_id": 19, "mode": "chat"})
        session_id = started.json()["session_id"]

        ended = client.post("/chat/end", json={"session_id": session_id})
        assert ended.status_code == 200

        blocked = client.post("/chat/message", json={"session_id": session_id, "text": "hello?"})
        assert blocked.status_code == 409


def test_default_teacher_responder_adds_rubric_without_openai_key(monkeypatch: Any) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = default_teacher_responder(
        {
            "user_input": "I did a mistake yesterday",
            "learner_profile": {"level": "A2"},
        }
    )
    assert response.rubric is not None
    assert 0 <= response.rubric.overall_score <= 100
    assert response.rubric.next_drill is not None
