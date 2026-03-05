from __future__ import annotations

import os
import json
from collections.abc import Callable
from typing import Any

import httpx
from openai import OpenAI

from app.config import settings
from app.models import LearnerProfile
from app.services.teacher import build_learner_profile_block

AsrTranscriberFn = Callable[[bytes, str, str, str], dict[str, str]]
VoiceTeacherFn = Callable[[str, LearnerProfile | None, str], str]


def default_asr_transcriber(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    language_hint: str,
) -> dict[str, str]:
    files = {"file": (filename, audio_bytes, content_type)}
    data = {"language_hint": language_hint}
    with httpx.Client(timeout=25.0) as client:
        response = client.post(f"{settings.asr_url}/asr/transcribe", files=files, data=data)
        response.raise_for_status()
        payload = response.json()
    return {"transcript": payload["transcript"], "language": payload.get("language", "unknown")}


def default_voice_teacher(transcript: str, profile: LearnerProfile | None, target_lang: str) -> str:
    profile_block = build_learner_profile_block(profile)
    preferences = profile_block.get("preferences", {}) or {}
    strictness = str(preferences.get("strictness", "medium")).lower()
    if strictness not in {"low", "medium", "high"}:
        strictness = "medium"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        opening = {
            "low": "Good attempt.",
            "medium": "Good practice.",
            "high": "Direct note.",
        }[strictness]
        return f"{opening} Let's continue in {target_lang}. You said: {transcript}"

    prompt = (
        "You are a language tutor. Reply briefly in target language practice mode "
        "and include one short correction if needed. "
        "Adapt tone to strictness: low=supportive, medium=balanced, high=direct."
    )
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": prompt},
            {
                "role": "developer",
                "content": json.dumps(
                    {
                        "learner_profile": profile_block,
                        "target_lang": target_lang,
                        "transcript": transcript,
                        "coaching_policy": {
                            "strictness": strictness,
                            "max_corrections": 1 if strictness == "low" else 2 if strictness == "medium" else 3,
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    return response.output_text.strip()


def build_pronunciation_feedback(transcript: str) -> str:
    rubric = build_pronunciation_rubric(transcript)
    if rubric["overall_score"] < 45:
        return "Focus on slower pace and clearer articulation. Start with short phrases."
    if rubric["overall_score"] < 70:
        return "Speech is understandable. Improve stress and sentence rhythm."
    return "Good pronunciation baseline. Keep polishing natural rhythm and intonation."


def build_pronunciation_rubric(transcript: str) -> dict[str, float | str | list[str]]:
    words = [w for w in transcript.split() if w.strip()]
    length = len(words)
    unique_ratio = len({w.lower() for w in words}) / max(1, length)
    has_contractions = any("'" in w for w in words)

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
