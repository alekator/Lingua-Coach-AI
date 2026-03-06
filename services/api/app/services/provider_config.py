from __future__ import annotations

import os

from app.config import settings


def _normalize_provider(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"openai", "local"}:
        return normalized
    return "openai"


def get_llm_provider() -> str:
    return _normalize_provider(os.getenv("API_LLM_PROVIDER", settings.api_llm_provider))


def get_asr_provider() -> str:
    return _normalize_provider(os.getenv("ASR_PROVIDER", "openai"))


def get_tts_provider() -> str:
    return _normalize_provider(os.getenv("TTS_PROVIDER", "openai"))


def set_runtime_providers(llm_provider: str, asr_provider: str, tts_provider: str) -> None:
    os.environ["API_LLM_PROVIDER"] = _normalize_provider(llm_provider)
    os.environ["ASR_PROVIDER"] = _normalize_provider(asr_provider)
    os.environ["TTS_PROVIDER"] = _normalize_provider(tts_provider)
