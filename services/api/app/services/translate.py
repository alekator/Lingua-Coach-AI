from __future__ import annotations

import os
from typing import Callable

import httpx
from openai import OpenAI

from app.config import settings
from app.services.ai_runtime import SmallLRUCache, log_usage, usage_from_response
from app.services.local_llm import complete_text, is_local_llm_enabled


TranslatorFn = Callable[[str, str, str], str]
TtsSynthesizerFn = Callable[[str, str, str], str]


_translate_cache = SmallLRUCache(max_items=settings.ai_cache_max_items)
_tts_cache = SmallLRUCache(max_items=settings.ai_cache_max_items)


def default_translator(text: str, source_lang: str, target_lang: str) -> str:
    clean_text = text.strip()[:1200]
    if not clean_text:
        return ""
    if source_lang.lower() == target_lang.lower():
        return clean_text

    cache_key = ("translate", source_lang.lower(), target_lang.lower(), clean_text.lower())
    cached = _translate_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    prompt = (
        "Translate the user text accurately.\n"
        f"Source language: {source_lang}\n"
        f"Target language: {target_lang}\n"
        "Return only translated text, no comments, no alternatives."
    )
    if is_local_llm_enabled():
        translated = complete_text(
            system_prompt=prompt,
            messages=[{"role": "user", "content": clean_text}],
            max_output_tokens=settings.openai_translate_max_output_tokens,
            temperature=settings.openai_temperature_translate,
        ).strip()
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            translated = f"[{source_lang}->{target_lang}] {clean_text}"
            _translate_cache.set(cache_key, translated)
            return translated
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=settings.openai_translate_model,
            max_output_tokens=settings.openai_translate_max_output_tokens,
            temperature=settings.openai_temperature_translate,
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": clean_text},
            ],
        )
        log_usage("translate", settings.openai_translate_model, usage_from_response(response))
        translated = response.output_text.strip()
    _translate_cache.set(cache_key, translated)
    return translated


def default_tts_synthesizer(text: str, target_lang: str, voice_name: str) -> str:
    clean_text = text.strip()
    cache_key = ("tts", target_lang.lower(), voice_name.lower(), clean_text)
    cached = _tts_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            f"{settings.tts_url}/tts/speak",
            json={"text": clean_text, "language": target_lang, "voice": voice_name},
        )
        response.raise_for_status()
        body = response.json()
    audio_url = body.get("audio_url")
    if not audio_url:
        raise ValueError("TTS service response missing audio_url")
    _tts_cache.set(cache_key, audio_url)
    return audio_url
