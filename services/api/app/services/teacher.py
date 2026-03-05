from __future__ import annotations

import json
from collections import Counter
from typing import Any, Callable

from openai import OpenAI

from app.models import LearnerProfile, Message, Mistake, VocabItem
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


def summarize_weak_topics(mistakes: list[Mistake]) -> list[str]:
    if not mistakes:
        return []
    ranked = Counter(m.category for m in mistakes if m.category).most_common(3)
    return [topic for topic, _ in ranked]


def build_teacher_payload(
    profile: LearnerProfile | None,
    mode: str,
    user_text: str,
    history: list[Message],
    recent_mistakes: list[Mistake] | None = None,
    active_vocab: list[VocabItem] | None = None,
) -> dict[str, Any]:
    compact_history = [{"role": msg.role, "text": msg.text} for msg in history[-8:]]
    mistakes = recent_mistakes or []
    vocab = active_vocab or []
    learner_profile = build_learner_profile_block(profile)
    learner_profile["weak_topics"] = summarize_weak_topics(mistakes)
    learner_profile["active_vocab"] = [
        {"word": item.word, "translation": item.translation} for item in vocab[-20:]
    ]

    return {
        "learner_profile": learner_profile,
        "mode": mode,
        "history": compact_history,
        "user_input": user_text,
        "recent_mistakes": [
            {
                "category": m.category,
                "bad": m.bad,
                "good": m.good,
                "explanation": m.explanation,
            }
            for m in mistakes[-8:]
        ],
        "coaching_policy": {
            "tone": "friendly_direct",
            "max_new_words": 2,
            "max_homework_items": 2,
            "must_reference_goal": True,
            "must_consider_weak_topics": True,
            "must_keep_reply_short_for_low_levels": True,
        },
        "schema": {
            "assistant_text": "string",
            "corrections": [
                {
                    "type": "grammar|vocab|pronunciation|fluency|style",
                    "bad": "string",
                    "good": "string",
                    "explanation": "string",
                }
            ],
            "new_words": [
                {
                    "word": "string",
                    "translation": "string",
                    "example": "string",
                    "phonetics": "string",
                }
            ],
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
        "You are LinguaCoach AI, a concise language coach. "
        "Always return strict JSON only with keys: assistant_text, corrections, new_words, homework_suggestions. "
        "No markdown, no prose outside JSON. "
        "Coach behavior rules: "
        "1) personalize by learner level, goal, weak_topics, and recent mistakes; "
        "2) keep assistant_text short and actionable; "
        "3) include at most 2 corrections and at most 2 new_words; "
        "4) corrections must be concrete bad->good transformations and explain briefly; "
        "5) prefer one next action aligned with learner goal."
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
