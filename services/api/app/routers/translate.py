from __future__ import annotations

from fastapi import APIRouter, Request

from app.config import settings
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services.translate import TranslatorFn, TtsSynthesizerFn
from app.db import get_db
from app.services.usage_budget import estimate_text_tokens, get_usage_budget_snapshot, record_usage_event
from sqlalchemy.orm import Session
from fastapi import Depends

router = APIRouter(tags=["translate"])


@router.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest, request: Request, db: Session = Depends(get_db)) -> TranslateResponse:
    translator: TranslatorFn = request.app.state.translator
    tts_synthesizer: TtsSynthesizerFn = request.app.state.tts_synthesizer
    if payload.user_id is not None:
        budget = get_usage_budget_snapshot(db, payload.user_id)
        if budget.blocked:
            return TranslateResponse(
                translated_text=payload.text,
                source_lang=payload.source_lang,
                target_lang=payload.target_lang,
                audio_url=None,
            )

    try:
        translated = translator(payload.text, payload.source_lang, payload.target_lang)
    except Exception:
        # Lightweight fallback for offline/degraded mode.
        translated = f"[{payload.source_lang}->{payload.target_lang}] {payload.text}"

    audio_url: str | None = None
    if payload.voice:
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
    )
