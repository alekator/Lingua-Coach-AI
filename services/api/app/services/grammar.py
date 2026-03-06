from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings
from app.schemas.learning import GrammarAnalyzeResponse, GrammarError
from app.services.ai_runtime import log_usage, usage_from_response
from app.services.local_llm import complete_json, is_local_llm_enabled
from app.services.openai_key_runtime import get_runtime_openai_key


def _fallback_grammar_analysis(text: str) -> GrammarAnalyzeResponse:
    corrected = text
    corrected = corrected.replace("I goed", "I went").replace("I has", "I have")
    corrected = corrected.replace("He go ", "He goes ").replace("She go ", "She goes ")
    errors: list[GrammarError] = []
    if corrected != text:
        errors.append(
            GrammarError(
                category="verb_form",
                bad=text,
                good=corrected,
                explanation="Use correct tense and verb form for the subject.",
            )
        )
    return GrammarAnalyzeResponse(
        corrected_text=corrected,
        errors=errors,
        exercises=[
            "Rewrite two sentences using correct verb forms.",
            "Write one sentence in present perfect using the same topic.",
        ],
    )


def _sanitize_response(raw: dict[str, Any], source_text: str) -> GrammarAnalyzeResponse:
    corrected_text = str(raw.get("corrected_text") or source_text).strip()
    raw_errors = raw.get("errors")
    parsed_errors: list[GrammarError] = []
    if isinstance(raw_errors, list):
        for item in raw_errors:
            if not isinstance(item, dict):
                continue
            bad = str(item.get("bad", "")).strip()
            good = str(item.get("good", "")).strip()
            if not bad or not good or bad == good:
                continue
            parsed_errors.append(
                GrammarError(
                    category=str(item.get("category") or "grammar").strip() or "grammar",
                    bad=bad,
                    good=good,
                    explanation=str(item.get("explanation") or "Improve grammar and word order.").strip(),
                )
            )
    raw_exercises = raw.get("exercises")
    parsed_exercises = [str(item).strip() for item in raw_exercises if str(item).strip()] if isinstance(raw_exercises, list) else []
    if not parsed_exercises:
        parsed_exercises = [
            "Rewrite the corrected sentence once from memory.",
            "Write one new sentence using the same grammar pattern.",
        ]
    return GrammarAnalyzeResponse(
        corrected_text=corrected_text,
        errors=parsed_errors[:5],
        exercises=parsed_exercises[:4],
    )


def analyze_grammar_with_ai(text: str, target_lang: str) -> GrammarAnalyzeResponse:
    clean_text = text.strip()
    if not clean_text:
        return _fallback_grammar_analysis(text)

    system_prompt = (
        "You are a strict grammar coach. Return strict JSON only with keys: corrected_text, errors, exercises.\n"
        "errors: array of objects {category, bad, good, explanation}.\n"
        "Rules:\n"
        "1) corrected_text must be natural and grammatically correct in target language.\n"
        "2) errors must be concrete bad->good transformations.\n"
        "3) keep explanations short and practical.\n"
        "4) include 2-4 short practice exercises."
    )
    user_payload = json.dumps({"target_lang": target_lang, "text": clean_text}, ensure_ascii=False)

    try:
        if is_local_llm_enabled():
            raw = complete_json(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_payload}],
                max_output_tokens=settings.openai_chat_max_output_tokens,
                temperature=settings.openai_temperature_chat,
            )
            return _sanitize_response(raw, clean_text)

        api_key = get_runtime_openai_key()
        if not api_key:
            return _fallback_grammar_analysis(text)
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=settings.openai_chat_model,
            max_output_tokens=settings.openai_chat_max_output_tokens,
            temperature=settings.openai_temperature_chat,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
        )
        log_usage("grammar_analyze", settings.openai_chat_model, usage_from_response(response))
        raw = json.loads(response.output_text)
        if not isinstance(raw, dict):
            return _fallback_grammar_analysis(text)
        return _sanitize_response(raw, clean_text)
    except Exception:
        return _fallback_grammar_analysis(text)
