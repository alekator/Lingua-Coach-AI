from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.schemas.chat import ChatMessageResponse, Correction, NewWord


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

        msg2 = client.post("/chat/message", json={"session_id": session_id, "text": "Thanks, understood"})
        assert msg2.status_code == 200
        assert len(payloads) == 2
        assert payloads[0]["learner_profile"]["level"] == "A2"
        assert payloads[1]["history"][0]["role"] == "user"
        assert payloads[1]["history"][1]["role"] == "assistant"
        assert "grammar" in payloads[1]["learner_profile"]["weak_topics"]
        assert payloads[1]["recent_mistakes"][0]["category"] == "grammar"
        assert any(word["word"] == "achieve" for word in payloads[1]["learner_profile"]["active_vocab"])


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
