from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi import HTTPException

from app.config import settings
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services.translate import TranslatorFn, TtsSynthesizerFn
from app.db import get_db
from app.services.usage_budget import estimate_text_tokens, get_usage_budget_snapshot, record_usage_event
from app.services.language_capabilities import is_speech_language_supported, validate_language_code
from app.services.local_llm import is_local_llm_enabled
from app.services.openai_key_runtime import get_runtime_openai_key
from app.services.provider_config import get_llm_provider
from sqlalchemy.orm import Session
from fastapi import Depends

router = APIRouter(tags=["translate"])


def _resolve_translation_engine() -> str:
    provider = get_llm_provider()
    local_available = is_local_llm_enabled()
    has_openai_key = bool(get_runtime_openai_key())
    if provider == "local":
        if local_available:
            return "local"
        if has_openai_key:
            return "openai"
        return "fallback"
    if has_openai_key:
        return "openai"
    if local_available:
        return "local"
    return "fallback"


@router.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest, request: Request, db: Session = Depends(get_db)) -> TranslateResponse:
    if payload.source_lang != "auto":
        try:
            payload.source_lang = validate_language_code(payload.source_lang)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        payload.target_lang = validate_language_code(payload.target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    translator: TranslatorFn = request.app.state.translator
    tts_synthesizer: TtsSynthesizerFn = request.app.state.tts_synthesizer
    engine_used = _resolve_translation_engine()
    if payload.user_id is not None:
        budget = get_usage_budget_snapshot(db, payload.user_id)
        if budget.blocked:
            return TranslateResponse(
                translated_text=payload.text,
                source_lang=payload.source_lang,
                target_lang=payload.target_lang,
                audio_url=None,
                engine_used="fallback",
            )

    try:
        translated = translator(payload.text, payload.source_lang, payload.target_lang)
    except Exception:
        # Lightweight fallback for offline/degraded mode.
        translated = f"[{payload.source_lang}->{payload.target_lang}] {payload.text}"
        engine_used = "fallback"

    audio_url: str | None = None
    if payload.voice:
        if not is_speech_language_supported(payload.target_lang):
            audio_url = None
        else:
            try:
                audio_url = tts_synthesizer(translated, payload.target_lang, payload.voice_name)
            except Exception:
                # Keep response successful and omit audio in degraded mode.
                audio_url = None

    if payload.user_id is not None:
        prompt_tokens = estimate_text_tokens(payload.text)
        output_tokens = estimate_text_tokens(translated)
        record_usage_event(
            db,
            user_id=payload.user_id,
            scope="translate",
            model=settings.openai_translate_model,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
        )
        db.commit()

    return TranslateResponse(
        translated_text=translated,
        source_lang=payload.source_lang,
        target_lang=payload.target_lang,
        audio_url=audio_url,
        engine_used=engine_used,
    )
