from __future__ import annotations

import os
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
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"Let's continue in {target_lang}. You said: {transcript}"

    profile_block = build_learner_profile_block(profile)
    prompt = (
        "You are a language tutor. Reply briefly in target language practice mode "
        "and include one short correction if needed."
    )
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": prompt},
            {
                "role": "developer",
                "content": str(
                    {
                        "learner_profile": profile_block,
                        "target_lang": target_lang,
                        "transcript": transcript,
                    }
                ),
            },
        ],
    )
    return response.output_text.strip()


def build_pronunciation_feedback(transcript: str) -> str:
    words = transcript.split()
    if len(words) < 4:
        return "Try speaking a little longer to assess pronunciation more accurately."
    if any("'" in w for w in words):
        return "Good contractions usage; focus on clear final consonants."
    return "Speech is understandable; focus on stress in longer words."
