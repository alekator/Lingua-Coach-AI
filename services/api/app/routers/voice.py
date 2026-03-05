from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LearnerProfile
from app.schemas.voice import VoiceMessageResponse, VoiceTranscribeResponse
from app.services.translate import TtsSynthesizerFn
from app.services.voice import (
    AsrTranscriberFn,
    VoiceTeacherFn,
    build_pronunciation_feedback,
    build_pronunciation_rubric,
)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def voice_transcribe(
    request: Request,
    file: UploadFile = File(...),
    language_hint: str = Form(default="auto"),
) -> VoiceTranscribeResponse:
    asr_transcriber: AsrTranscriberFn = request.app.state.asr_transcriber
    audio_bytes = await file.read()
    try:
        result = asr_transcriber(
            audio_bytes,
            file.filename or "audio.webm",
            file.content_type or "audio/webm",
            language_hint,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ASR failed: {exc}") from exc

    return VoiceTranscribeResponse(
        transcript=result["transcript"],
        language=result.get("language", "unknown"),
    )


@router.post("/message", response_model=VoiceMessageResponse)
async def voice_message(
    request: Request,
    file: UploadFile = File(...),
    user_id: int | None = Form(default=None),
    target_lang: str = Form(default="en"),
    language_hint: str = Form(default="auto"),
    voice_name: str = Form(default="alloy"),
    db: Session = Depends(get_db),
) -> VoiceMessageResponse:
    asr_transcriber: AsrTranscriberFn = request.app.state.asr_transcriber
    voice_teacher: VoiceTeacherFn = request.app.state.voice_teacher
    tts_synthesizer: TtsSynthesizerFn = request.app.state.tts_synthesizer

    audio_bytes = await file.read()
    try:
        asr_result = asr_transcriber(
            audio_bytes,
            file.filename or "audio.webm",
            file.content_type or "audio/webm",
            language_hint,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ASR failed: {exc}") from exc

    transcript = asr_result["transcript"]
    profile = None if user_id is None else db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    teacher_text = voice_teacher(transcript, profile, target_lang)

    try:
        audio_url = tts_synthesizer(teacher_text, target_lang, voice_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc

    return VoiceMessageResponse(
        transcript=transcript,
        teacher_text=teacher_text,
        audio_url=audio_url,
        pronunciation_feedback=build_pronunciation_feedback(transcript),
        pronunciation_rubric=build_pronunciation_rubric(transcript),
    )
