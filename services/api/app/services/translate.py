from __future__ import annotations

import os
from typing import Callable

import httpx
from openai import OpenAI

from app.config import settings


TranslatorFn = Callable[[str, str, str], str]
TtsSynthesizerFn = Callable[[str, str, str], str]


def default_translator(text: str, source_lang: str, target_lang: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"[{source_lang}->{target_lang}] {text}"

    client = OpenAI(api_key=api_key)
    prompt = (
        "Translate the user text accurately.\n"
        f"Source language: {source_lang}\n"
        f"Target language: {target_lang}\n"
        "Return only translated text, no comments."
    )
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
    )
    return response.output_text.strip()


def default_tts_synthesizer(text: str, target_lang: str, voice_name: str) -> str:
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            f"{settings.tts_url}/tts/speak",
            json={"text": text, "language": target_lang, "voice": voice_name},
        )
        response.raise_for_status()
        body = response.json()
    audio_url = body.get("audio_url")
    if not audio_url:
        raise ValueError("TTS service response missing audio_url")
    return audio_url
