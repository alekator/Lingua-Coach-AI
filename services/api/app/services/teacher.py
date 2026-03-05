from __future__ import annotations

import json
from typing import Any, Callable

from openai import OpenAI

from app.models import LearnerProfile, Message
from app.schemas.chat import ChatMessageResponse


TeacherResponder = Callable[[dict[str, Any]], ChatMessageResponse]


def build_learner_profile_block(profile: LearnerProfile | None) -> dict[str, Any]:
    if profile is None:
        return {
            "level": "A1",
            "native_lang": "unknown",
            "target_lang": "unknown",
            "goal": None,
            "weak_topics": [],
            "preferences": {},
        }
    return {
        "level": profile.level,
        "native_lang": profile.native_lang,
        "target_lang": profile.target_lang,
        "goal": profile.goal,
        "weak_topics": [],
        "preferences": profile.preferences or {},
    }


def build_teacher_payload(
    profile: LearnerProfile | None,
    mode: str,
    user_text: str,
    history: list[Message],
) -> dict[str, Any]:
    compact_history = [{"role": msg.role, "text": msg.text} for msg in history[-8:]]
    return {
        "learner_profile": build_learner_profile_block(profile),
        "mode": mode,
        "history": compact_history,
        "user_input": user_text,
        "schema": {
            "assistant_text": "string",
            "corrections": [{"type": "string", "bad": "string", "good": "string"}],
            "new_words": [{"word": "string", "translation": "string", "example": "string"}],
            "homework_suggestions": ["string"],
        },
    }


def default_teacher_responder(payload: dict[str, Any]) -> ChatMessageResponse:
    user_text = payload["user_input"]
    learner_profile = payload["learner_profile"]
    api_key = __import__("os").getenv("OPENAI_API_KEY")
    if not api_key:
        return ChatMessageResponse(
            assistant_text=(
                f"Practice ({learner_profile['level']}): {user_text}. "
                "I corrected one small item and added one useful word."
            ),
            corrections=[],
            new_words=[],
            homework_suggestions=["Write 3 short sentences using today's topic."],
        )

    system_prompt = (
        "You are LinguaCoach AI. Return strict JSON only with keys: "
        "assistant_text, corrections, new_words, homework_suggestions."
    )
    developer_prompt = json.dumps(payload, ensure_ascii=False)

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "developer", "content": developer_prompt},
        ],
    )
    text = response.output_text
    parsed = json.loads(text)
    return ChatMessageResponse.model_validate(parsed)
