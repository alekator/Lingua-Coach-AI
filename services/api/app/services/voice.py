from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
from openai import OpenAI

from app.config import settings
from app.models import LearnerProfile
from app.services.ai_runtime import SmallLRUCache, log_usage, usage_from_response
from app.services.local_llm import complete_text, is_local_llm_enabled
from app.services.openai_key_runtime import get_runtime_openai_key
from app.services.teacher import build_learner_profile_block
from app.services.text_metrics import lexical_diversity, text_units

AsrTranscriberFn = Callable[[bytes, str, str, str], dict[str, str]]
VoiceTeacherFn = Callable[[str, LearnerProfile | None, str], str]
_voice_teacher_cache = SmallLRUCache(max_items=settings.ai_cache_max_items)


def default_asr_transcriber(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    language_hint: str,
) -> dict[str, str]:
    files = {"file": (filename, audio_bytes, content_type)}
    data = {"language_hint": language_hint}
    headers: dict[str, str] = {}
    api_key = get_runtime_openai_key()
    if api_key:
        headers["X-OpenAI-API-Key"] = api_key
    with httpx.Client(timeout=25.0) as client:
        response = client.post(f"{settings.asr_url}/asr/transcribe", files=files, data=data, headers=headers)
        response.raise_for_status()
        payload = response.json()
    return {"transcript": payload["transcript"], "language": payload.get("language", "unknown")}


def default_voice_teacher(transcript: str, profile: LearnerProfile | None, target_lang: str) -> str:
    clean_transcript = transcript.strip()[:900]
    profile_block = build_learner_profile_block(profile)
    weak_topics = profile_block.get("weak_topics", []) or []
    top_weak = weak_topics[0] if weak_topics else "fluency"
    goal = str(profile_block.get("goal") or "daily communication")
    preferences = profile_block.get("preferences", {}) or {}
    strictness = str(preferences.get("strictness", "medium")).lower()
    if strictness not in {"low", "medium", "high"}:
        strictness = "medium"
    persona_style = str(preferences.get("persona_style", "coach")).lower()
    if persona_style not in {"coach", "friendly", "examiner"}:
        persona_style = "coach"

    cache_key = ("voice_teacher", target_lang.lower(), strictness, persona_style, clean_transcript.lower())
    cached = _voice_teacher_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    prompt = (
        "You are a language tutor. Reply briefly in target language practice mode "
        "and include one short correction if needed. "
        "Adapt tone to strictness: low=supportive, medium=balanced, high=direct. "
        "Be human and specific: mention one concrete next micro-step for this learner goal."
    )
    payload_text = json.dumps(
        {
            "learner_profile": profile_block,
            "target_lang": target_lang,
            "transcript": clean_transcript,
            "coaching_policy": {
                "strictness": strictness,
                "persona_style": persona_style,
                "goal": goal,
                "top_weak_topic": top_weak,
                "max_corrections": 1 if strictness == "low" else 2 if strictness == "medium" else 3,
            },
        },
        ensure_ascii=False,
    )
    if is_local_llm_enabled():
        teacher_text = complete_text(
            system_prompt=prompt,
            messages=[{"role": "user", "content": payload_text}],
            max_output_tokens=settings.openai_voice_max_output_tokens,
            temperature=settings.openai_temperature_voice,
        ).strip()
    else:
        api_key = get_runtime_openai_key()
        if not api_key:
            opening = {
                "low": "Nice voice attempt.",
                "medium": "Good practice run.",
                "high": "Straight feedback:",
            }[strictness]
            quick_fix = ""
            lower_text = clean_transcript.lower()
            if "goed" in lower_text:
                quick_fix = " Quick fix: say 'went' instead of 'goed'."
            fallback = (
                f"{opening} We keep it in {target_lang}. Goal: {goal}. "
                f"Focus now: {top_weak}. You said: {clean_transcript}.{quick_fix} "
                "Next micro-step: record one shorter retry."
            )
            _voice_teacher_cache.set(cache_key, fallback)
            return fallback
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=settings.openai_voice_model,
            max_output_tokens=settings.openai_voice_max_output_tokens,
            temperature=settings.openai_temperature_voice,
            input=[
                {"role": "system", "content": prompt},
                {"role": "developer", "content": payload_text},
            ],
        )
        log_usage("voice_teacher", settings.openai_voice_model, usage_from_response(response))
        teacher_text = response.output_text.strip()
    _voice_teacher_cache.set(cache_key, teacher_text)
    return teacher_text


def build_pronunciation_feedback(transcript: str) -> str:
    rubric = build_pronunciation_rubric(transcript)
    top_tip = str(rubric.get("actionable_tips", ["Keep practicing."])[0])
    if rubric["overall_score"] < 45:
        return f"Let's slow it down and make each word clearer. {top_tip}"
    if rubric["overall_score"] < 70:
        return f"Your message is understandable. Next, improve stress and sentence rhythm. {top_tip}"
    return f"Strong pronunciation baseline. Keep polishing natural rhythm and intonation. {top_tip}"


def build_pronunciation_rubric(transcript: str) -> dict[str, float | str | list[str]]:
    length = text_units(transcript)
    unique_ratio = lexical_diversity(transcript)
    has_contractions = "'" in transcript

    fluency = 35.0 + min(45.0, length * 2.5)
    clarity = 50.0 + (10.0 if has_contractions else 0.0)
    grammar_accuracy = 75.0 if "goed" not in transcript.lower() else 45.0
    vocabulary_range = min(90.0, 40.0 + unique_ratio * 55.0)
    confidence = min(90.0, 35.0 + length * 2.0)

    overall = round(
        0.25 * fluency
        + 0.2 * clarity
        + 0.2 * grammar_accuracy
        + 0.15 * vocabulary_range
        + 0.2 * confidence,
        2,
    )
    band = "needs_work" if overall < 45 else "developing" if overall < 70 else "solid"
    tips: list[str] = []
    if fluency < 60:
        tips.append("Speak in 5-8 word chunks without long pauses.")
    if clarity < 65:
        tips.append("Over-articulate final consonants, then relax naturally.")
    if grammar_accuracy < 60:
        tips.append("Review irregular past forms before speaking drills.")
    if vocabulary_range < 60:
        tips.append("Reuse 3-5 topic words in one response.")
    if not tips:
        tips.append("Add intonation variety on key words for natural delivery.")

    return {
        "fluency": round(fluency, 2),
        "clarity": round(clarity, 2),
        "grammar_accuracy": round(grammar_accuracy, 2),
        "vocabulary_range": round(vocabulary_range, 2),
        "confidence": round(confidence, 2),
        "overall_score": overall,
        "level_band": band,
        "actionable_tips": tips[:3],
    }
