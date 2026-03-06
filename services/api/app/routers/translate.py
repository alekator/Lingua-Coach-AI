from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

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
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}") from exc

    audio_url: str | None = None
    if payload.voice:
        try:
            audio_url = tts_synthesizer(translated, payload.target_lang, payload.voice_name)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc

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
