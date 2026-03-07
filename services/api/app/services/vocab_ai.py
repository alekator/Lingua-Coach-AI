from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings
from app.services.ai_runtime import log_usage, usage_from_response
from app.services.local_llm import complete_json, is_local_llm_enabled
from app.services.openai_key_runtime import get_runtime_openai_key
from app.services.provider_config import get_llm_provider


def _fallback_enrichment(word: str, translation: str) -> dict[str, str | None]:
    clean_word = word.strip()
    clean_translation = translation.strip()
    example = f"{clean_word.capitalize()} means {clean_translation}."
    return {
        "translation": clean_translation,
        "example": example,
        "phonetics": None,
        "source": "fallback",
    }


def _sanitize_enrichment(raw: dict[str, Any], word: str, translation: str) -> dict[str, str | None]:
    fallback = _fallback_enrichment(word, translation)
    parsed_translation = str(raw.get("translation") or "").strip()
    parsed_example = str(raw.get("example") or "").strip()
    parsed_phonetics = str(raw.get("phonetics") or "").strip()

    if not parsed_translation:
        parsed_translation = fallback["translation"] or translation.strip()
    if not parsed_example:
        parsed_example = fallback["example"] or f"{word.strip()}."
    if len(parsed_example) > 2000:
        parsed_example = parsed_example[:2000].strip()
    if len(parsed_translation) > 255:
        parsed_translation = parsed_translation[:255].strip()
    if parsed_phonetics and len(parsed_phonetics) > 100:
        parsed_phonetics = parsed_phonetics[:100].strip()
    return {
        "translation": parsed_translation,
        "example": parsed_example,
        "phonetics": parsed_phonetics or None,
        "source": str(raw.get("source") or "").strip().lower() or None,
    }


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start >= 0 and end > start:
        candidate = raw_text[start : end + 1]
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Vocab enrichment response is not valid JSON")


def _build_prompt_payload(word: str, translation: str, native_lang: str, target_lang: str) -> str:
    return json.dumps(
        {
            "word": word,
            "translation": translation,
            "native_lang": native_lang,
            "target_lang": target_lang,
        },
        ensure_ascii=False,
    )


def _enrich_with_local(word: str, translation: str, native_lang: str, target_lang: str) -> dict[str, str | None]:
    payload = complete_json(
        system_prompt=(
            "You are a vocabulary coach. Return strict JSON only with keys: translation, example, phonetics.\n"
            "Rules:\n"
            "1) Keep translation concise and natural for native language.\n"
            "2) example must be one short practical sentence in target language using the word.\n"
            "3) phonetics should be short IPA-like hint when possible, otherwise empty string.\n"
        ),
        messages=[{"role": "user", "content": _build_prompt_payload(word, translation, native_lang, target_lang)}],
        max_output_tokens=settings.openai_chat_max_output_tokens,
        temperature=settings.openai_temperature_chat,
    )
    enriched = _sanitize_enrichment(payload, word, translation)
    enriched["source"] = "local"
    return enriched


def _enrich_with_openai(word: str, translation: str, native_lang: str, target_lang: str) -> dict[str, str | None]:
    api_key = get_runtime_openai_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=settings.openai_chat_model,
        max_output_tokens=settings.openai_chat_max_output_tokens,
        temperature=settings.openai_temperature_chat,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a vocabulary coach. Return strict JSON only with keys: translation, example, phonetics.\n"
                    "Rules:\n"
                    "1) Keep translation concise and natural for native language.\n"
                    "2) example must be one short practical sentence in target language using the word.\n"
                    "3) phonetics should be short IPA-like hint when possible, otherwise empty string.\n"
                ),
            },
            {"role": "user", "content": _build_prompt_payload(word, translation, native_lang, target_lang)},
        ],
    )
    log_usage("vocab_enrich", settings.openai_chat_model, usage_from_response(response))
    parsed = _extract_json_object(response.output_text)
    enriched = _sanitize_enrichment(parsed, word, translation)
    enriched["source"] = "openai"
    return enriched


def enrich_vocab_entry(
    word: str,
    translation: str,
    *,
    native_lang: str = "en",
    target_lang: str = "en",
) -> dict[str, str | None]:
    clean_word = word.strip()
    clean_translation = translation.strip()
    if not clean_word or not clean_translation:
        return _fallback_enrichment(clean_word, clean_translation)
    try:
        provider = get_llm_provider()
        local_available = is_local_llm_enabled()
        has_openai_key = bool(get_runtime_openai_key())

        if provider == "local":
            if local_available:
                try:
                    return _enrich_with_local(clean_word, clean_translation, native_lang, target_lang)
                except Exception:
                    pass
            if has_openai_key:
                return _enrich_with_openai(clean_word, clean_translation, native_lang, target_lang)
            return _fallback_enrichment(clean_word, clean_translation)

        if has_openai_key:
            try:
                return _enrich_with_openai(clean_word, clean_translation, native_lang, target_lang)
            except Exception:
                pass
        if local_available:
            return _enrich_with_local(clean_word, clean_translation, native_lang, target_lang)
        return _fallback_enrichment(clean_word, clean_translation)
    except Exception:
        return _fallback_enrichment(clean_word, clean_translation)
