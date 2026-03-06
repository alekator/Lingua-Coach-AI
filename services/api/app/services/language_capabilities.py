from __future__ import annotations

import re
from dataclasses import dataclass


LANGUAGE_CODE_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$")

# Full text pipeline works for any valid language code (LLM translation/chat fallback).
SPEECH_LANGS = {
    "en",
    "es",
    "de",
    "fr",
    "ru",
    "it",
    "pt",
    "ja",
    "ko",
    "zh",
    "ar",
    "hi",
    "tr",
    "nl",
    "pl",
    "uk",
}


def normalize_lang_code(lang: str) -> str:
    return lang.strip().lower().replace("_", "-")


def validate_language_code(lang: str) -> str:
    normalized = normalize_lang_code(lang)
    if not normalized:
        raise ValueError("Language code must not be empty")
    if not LANGUAGE_CODE_RE.match(normalized):
        raise ValueError(f"Invalid language code: '{lang}'")
    return normalized


def validate_language_pair(native_lang: str, target_lang: str) -> tuple[str, str]:
    native = validate_language_code(native_lang)
    target = validate_language_code(target_lang)
    if native == target:
        raise ValueError("Native and target language must be different")
    return native, target


def _speech_support(lang: str) -> bool:
    base = lang.split("-", 1)[0]
    return base in SPEECH_LANGS


def is_speech_language_supported(lang: str) -> bool:
    code = validate_language_code(lang)
    return _speech_support(code)


@dataclass(frozen=True)
class LanguagePairCapabilities:
    native_lang: str
    target_lang: str
    text_supported: bool
    asr_supported: bool
    tts_supported: bool
    voice_supported: bool
    recommendation: str


def get_pair_capabilities(native_lang: str, target_lang: str) -> LanguagePairCapabilities:
    native, target = validate_language_pair(native_lang, target_lang)
    asr_supported = _speech_support(target)
    tts_supported = _speech_support(target)
    voice_supported = asr_supported and tts_supported
    if voice_supported:
        recommendation = "Full mode: chat, translate, and voice are available."
    else:
        recommendation = "Text mode is fully supported. Voice may run in limited fallback for this target language."
    return LanguagePairCapabilities(
        native_lang=native,
        target_lang=target,
        text_supported=True,
        asr_supported=asr_supported,
        tts_supported=tts_supported,
        voice_supported=voice_supported,
        recommendation=recommendation,
    )
