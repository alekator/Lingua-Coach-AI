from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services.translate import TranslatorFn, TtsSynthesizerFn

router = APIRouter(tags=["translate"])


@router.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest, request: Request) -> TranslateResponse:
    translator: TranslatorFn = request.app.state.translator
    tts_synthesizer: TtsSynthesizerFn = request.app.state.tts_synthesizer

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

    return TranslateResponse(
        translated_text=translated,
        source_lang=payload.source_lang,
        target_lang=payload.target_lang,
        audio_url=audio_url,
    )
