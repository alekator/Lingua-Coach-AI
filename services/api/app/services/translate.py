from __future__ import annotations

from typing import Callable
from urllib.parse import urlparse

import httpx
from openai import OpenAI

from app.config import settings
from app.services.ai_runtime import SmallLRUCache, log_usage, usage_from_response
from app.services.local_llm import complete_text, is_local_llm_enabled
from app.services.openai_key_runtime import get_runtime_openai_key


TranslatorFn = Callable[[str, str, str], str]
TtsSynthesizerFn = Callable[[str, str, str], str]


_translate_cache = SmallLRUCache(max_items=settings.ai_cache_max_items)
_tts_cache = SmallLRUCache(max_items=settings.ai_cache_max_items)


def _tts_candidate_urls() -> list[str]:
    primary = settings.tts_url.rstrip("/")
    candidates: list[str] = [primary]
    parsed = urlparse(primary)
    host = (parsed.hostname or "").lower()
    # When API runs on host machine and .env keeps docker aliases (tts/asr),
    # try localhost fallback automatically to avoid runtime TTS failures.
    if host in {"tts", "host.docker.internal"}:
        fallback = "http://localhost:8002"
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


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
        api_key = get_runtime_openai_key()
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

    headers: dict[str, str] = {}
    api_key = get_runtime_openai_key()
    if api_key:
        headers["X-OpenAI-API-Key"] = api_key
    last_exc: Exception | None = None
    body: dict[str, str] | None = None
    with httpx.Client(timeout=20.0) as client:
        for base_url in _tts_candidate_urls():
            try:
                response = client.post(
                    f"{base_url}/tts/speak",
                    json={"text": clean_text, "language": target_lang, "voice": voice_name},
                    headers=headers,
                )
                response.raise_for_status()
                body = response.json()
                break
            except Exception as exc:  # pragma: no cover - exercised in runtime and dedicated tests
                last_exc = exc
                continue
    if body is None:
        raise RuntimeError(f"TTS service unavailable via configured endpoints: {last_exc}") from last_exc
    audio_url = body.get("audio_url")
    if not audio_url:
        raise ValueError("TTS service response missing audio_url")
    _tts_cache.set(cache_key, audio_url)
    return audio_url
