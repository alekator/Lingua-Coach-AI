from __future__ import annotations

import json
from collections import Counter
from typing import Any, Callable

from openai import OpenAI

from app.config import settings
from app.models import LearnerProfile, Message, Mistake, VocabItem
from app.services.ai_runtime import log_usage, usage_from_response
from app.services.text_metrics import text_units
from app.schemas.chat import ChatMessageResponse, ChatRubric, ChatRubricDimension


TeacherResponder = Callable[[dict[str, Any]], ChatMessageResponse]


def _rubric_band(score: int) -> str:
    if score >= 85:
        return "strong"
    if score >= 70:
        return "developing"
    return "foundation"


def build_fallback_rubric(user_text: str, response: ChatMessageResponse) -> ChatRubric:
    words = max(1, text_units(user_text))
    corrections_count = len(response.corrections)
    base_score = 78 if words >= 6 else 68
    penalty = min(18, corrections_count * 7)
    overall_score = max(35, min(95, base_score - penalty))

    grammar_score = max(1, min(5, 5 - corrections_count))
    lexical_score = 4 if words >= 10 else 3 if words >= 5 else 2
    fluency_score = 4 if words >= 8 else 3 if words >= 4 else 2
    task_score = 4 if words >= 5 else 2

    strengths: list[str] = []
    if words >= 6:
        strengths.append("Good attempt to express a complete thought.")
    if response.new_words:
        strengths.append("You can reuse new vocabulary from this turn.")
    if not strengths:
        strengths.append("You are practicing consistently.")

    priority_fixes = [
        f"{c.bad} -> {c.good}" if not c.explanation else f"{c.bad} -> {c.good}: {c.explanation}"
        for c in response.corrections[:2]
    ]
    if not priority_fixes:
        priority_fixes = ["Keep sentence structure simple and accurate."]

    next_drill: str | None = None
    if response.corrections:
        next_drill = f"Write 3 short sentences applying the {response.corrections[0].type} fix."
    elif response.homework_suggestions:
        next_drill = response.homework_suggestions[0]

    return ChatRubric(
        overall_score=overall_score,
        level_band=_rubric_band(overall_score),
        grammar_accuracy=ChatRubricDimension(
            score=grammar_score,
            feedback="Focus on one grammar pattern from the latest correction.",
        ),
        lexical_range=ChatRubricDimension(
            score=lexical_score,
            feedback="Reuse target vocabulary in your next 2-3 sentences.",
        ),
        fluency_coherence=ChatRubricDimension(
            score=fluency_score,
            feedback="Keep replies in one clear idea per sentence.",
        ),
        task_completion=ChatRubricDimension(
            score=task_score,
            feedback="Answer directly and add one useful detail.",
        ),
        strengths=strengths,
        priority_fixes=priority_fixes,
        next_drill=next_drill,
    )


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


def _normalize_strictness(preferences: dict[str, Any]) -> str:
    raw = str(preferences.get("strictness", "medium")).lower()
    if raw in {"low", "medium", "high"}:
        return raw
    return "medium"


def _normalize_daily_minutes(preferences: dict[str, Any]) -> int:
    raw = preferences.get("daily_minutes", 15)
    if isinstance(raw, int):
        return max(5, min(180, raw))
    return 15


def _normalize_persona_style(preferences: dict[str, Any]) -> str:
    raw = str(preferences.get("persona_style", "coach")).lower()
    if raw in {"coach", "friendly", "examiner"}:
        return raw
    return "coach"


def _build_coaching_policy(profile: LearnerProfile | None) -> dict[str, Any]:
    prefs = (profile.preferences if profile else {}) or {}
    strictness = _normalize_strictness(prefs)
    daily_minutes = _normalize_daily_minutes(prefs)
    persona_style = _normalize_persona_style(prefs)
    level = (profile.level if profile else "A1").upper()

    max_corrections = {"low": 1, "medium": 2, "high": 3}[strictness]
    tone = {"low": "supportive_coach", "medium": "friendly_direct", "high": "direct_coach"}[strictness]
    session_intensity = "light" if daily_minutes <= 12 else "balanced" if daily_minutes <= 30 else "intense"
    reply_style = "very_short" if level in {"A1", "A2"} else "short"

    return {
        "tone": tone,
        "strictness": strictness,
        "daily_minutes": daily_minutes,
        "session_intensity": session_intensity,
        "reply_style": reply_style,
        "persona_style": persona_style,
        "max_corrections": max_corrections,
        "max_new_words": 2,
        "max_homework_items": 2,
        "must_reference_goal": True,
        "must_consider_weak_topics": True,
        "must_keep_reply_short_for_low_levels": True,
        "must_sound_human": True,
        "must_avoid_repetitive_openers": True,
        "must_return_rubric": True,
    }


def build_resilient_teacher_fallback(payload: dict[str, Any], reason: str | None = None) -> ChatMessageResponse:
    user_text = str(payload.get("user_input", "")).strip() or "your latest message"
    learner_profile = payload.get("learner_profile", {}) or {}
    level = str(learner_profile.get("level", "A1"))
    goal = str(learner_profile.get("goal") or "general communication")
    weak_topics = learner_profile.get("weak_topics", []) or []
    top_weak = str(weak_topics[0]) if weak_topics else "grammar"
    preferences = learner_profile.get("preferences", {}) or {}
    strictness = _normalize_strictness(preferences)
    opener, action_template = {
        "low": ("Nice try.", "Micro-step: rewrite it once with simpler words."),
        "medium": ("Solid attempt.", "Micro-step: rewrite it once with one clean correction."),
        "high": ("Direct feedback.", "Micro-step: rewrite it now with precise grammar and one detail."),
    }[strictness]
    recovery_note = "I switched to local fallback guidance for this turn."
    if reason:
        recovery_note = f"{recovery_note} Reason: {reason[:80]}."

    response = ChatMessageResponse(
        assistant_text=(
            f"{opener} Goal focus: {goal}. "
            f"Practice ({level}) on {top_weak}: {user_text}. "
            f"{action_template} {recovery_note}"
        ),
        corrections=[],
        new_words=[],
        homework_suggestions=[f"Write 3 short lines about {goal} with clean {top_weak}."],
    )
    response.rubric = build_fallback_rubric(user_text, response)
    return response


def summarize_weak_topics(mistakes: list[Mistake]) -> list[str]:
    if not mistakes:
        return []
    ranked = Counter(m.category for m in mistakes if m.category).most_common(3)
    return [topic for topic, _ in ranked]


def sanitize_teacher_response(
    response: ChatMessageResponse,
    payload: dict[str, Any],
) -> ChatMessageResponse:
    policy = payload.get("coaching_policy", {}) or {}
    max_corrections = int(policy.get("max_corrections", 2))
    max_homework_items = int(policy.get("max_homework_items", 2))
    cleaned = []
    filtered_out = 0
    for correction in response.corrections:
        bad = correction.bad.strip()
        good = correction.good.strip()
        if not bad or not good:
            filtered_out += 1
            continue
        if bad.lower() == good.lower():
            filtered_out += 1
            continue
        if len(bad) > 180 or len(good) > 180:
            filtered_out += 1
            continue
        cleaned.append(correction)

    response.corrections = cleaned[:max_corrections]
    response.homework_suggestions = response.homework_suggestions[:max_homework_items]
    if filtered_out > 0:
        response.homework_suggestions.append(
            "One correction was skipped for reliability; rewrite your sentence in a simpler form."
        )
    if not response.assistant_text.strip():
        response.assistant_text = "Good effort. Try one clearer sentence and we will refine it together."
    if response.rubric is None:
        response.rubric = build_fallback_rubric(str(payload.get("user_input", "")), response)
    return response


def build_teacher_payload(
    profile: LearnerProfile | None,
    mode: str,
    user_text: str,
    history: list[Message],
    recent_mistakes: list[Mistake] | None = None,
    active_vocab: list[VocabItem] | None = None,
) -> dict[str, Any]:
    compact_history = [
        {"role": msg.role, "text": msg.text[:280]}
        for msg in history[-6:]
    ]
    mistakes = recent_mistakes or []
    vocab = active_vocab or []
    learner_profile = build_learner_profile_block(profile)
    learner_profile["weak_topics"] = summarize_weak_topics(mistakes)
    learner_profile["active_vocab"] = [
        {"word": item.word, "translation": item.translation} for item in vocab[-8:]
    ]

    coaching_policy = _build_coaching_policy(profile)
    top_weak = learner_profile["weak_topics"][0] if learner_profile["weak_topics"] else "grammar"
    focus_word = learner_profile["active_vocab"][0]["word"] if learner_profile["active_vocab"] else None

    return {
        "learner_profile": learner_profile,
        "mode": mode,
        "history": compact_history,
        "user_input": user_text[:900],
        "session_context": {
            "top_weak_topic": top_weak,
            "focus_word": focus_word,
            "history_turns": len(compact_history),
            "target_behavior": "sound natural and specific, not generic",
        },
        "recent_mistakes": [
            {
                "category": m.category,
                "bad": m.bad[:160],
                "good": m.good[:160],
                "explanation": None if m.explanation is None else m.explanation[:180],
            }
            for m in mistakes[-5:]
        ],
        "coaching_policy": coaching_policy,
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
            "rubric": {
                "overall_score": "integer 0..100",
                "level_band": "foundation|developing|strong",
                "grammar_accuracy": {"score": "integer 1..5", "feedback": "string"},
                "lexical_range": {"score": "integer 1..5", "feedback": "string"},
                "fluency_coherence": {"score": "integer 1..5", "feedback": "string"},
                "task_completion": {"score": "integer 1..5", "feedback": "string"},
                "strengths": ["string"],
                "priority_fixes": ["string"],
                "next_drill": "string",
            },
        },
    }


def default_teacher_responder(payload: dict[str, Any]) -> ChatMessageResponse:
    user_text = payload["user_input"]
    api_key = __import__("os").getenv("OPENAI_API_KEY")
    if not api_key:
        return build_resilient_teacher_fallback(payload, reason="OPENAI_API_KEY missing")

    system_prompt = (
        "You are LinguaCoach AI, a concise language coach. "
        "Always return strict JSON only with keys: assistant_text, corrections, new_words, homework_suggestions, rubric. "
        "No markdown, no prose outside JSON. "
        "Coach behavior rules: "
        "1) personalize by learner level, goal, weak_topics, recent mistakes, and strictness; "
        "2) keep assistant_text short and actionable; "
        "3) follow max_corrections/max_new_words from coaching_policy; "
        "4) corrections must be concrete bad->good transformations and explain briefly; "
        "5) prefer one next action aligned with learner goal and session intensity; "
        "6) vary opener phrasing and avoid repetitive generic intros; "
        "7) when possible, include one realistic mini-example for user's context."
    )
    developer_prompt = json.dumps(payload, ensure_ascii=False)

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model=settings.openai_chat_model,
            max_output_tokens=settings.openai_chat_max_output_tokens,
            temperature=settings.openai_temperature_chat,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "developer", "content": developer_prompt},
            ],
        )
        log_usage("chat_teacher", settings.openai_chat_model, usage_from_response(response))
        text = response.output_text
        parsed = json.loads(text)
        result = ChatMessageResponse.model_validate(parsed)
        return sanitize_teacher_response(result, payload)
    except Exception as exc:
        return build_resilient_teacher_fallback(payload, reason=f"provider error: {exc}")
