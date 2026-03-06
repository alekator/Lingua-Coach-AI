from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.config import settings
from app.models import LearnerProfile, Mistake, SkillSnapshot
from app.schemas.voice import VoiceMessageResponse, VoiceProgressPoint, VoiceProgressResponse, VoiceTranscribeResponse
from app.services.translate import TtsSynthesizerFn
from app.services.usage_budget import estimate_text_tokens, get_usage_budget_snapshot, record_usage_event
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
    target_lang: str | None = Form(default=None),
    language_hint: str = Form(default="auto"),
    voice_name: str = Form(default="alloy"),
    db: Session = Depends(get_db),
) -> VoiceMessageResponse:
    asr_transcriber: AsrTranscriberFn = request.app.state.asr_transcriber
    voice_teacher: VoiceTeacherFn = request.app.state.voice_teacher
    tts_synthesizer: TtsSynthesizerFn = request.app.state.tts_synthesizer
    if user_id is not None:
        budget = get_usage_budget_snapshot(db, user_id)
        if budget.blocked:
            blocked_text = (
                "Budget cap reached for this period. "
                "Voice AI is paused; continue with text chat or increase limits in Profile."
            )
            return VoiceMessageResponse(
                transcript="",
                teacher_text=blocked_text,
                audio_url="offline://budget-blocked",
                pronunciation_feedback="Voice scoring paused due to budget cap.",
                pronunciation_rubric=build_pronunciation_rubric(""),
            )

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
    resolved_target_lang = (
        (target_lang.strip().lower() if target_lang and target_lang.strip() else None)
        or (profile.target_lang if profile is not None else None)
        or "en"
    )
    try:
        teacher_text = voice_teacher(transcript, profile, resolved_target_lang)
    except Exception:
        teacher_text = (
            f"Fallback coach mode in {resolved_target_lang}: {transcript}. "
            "Try one shorter and cleaner version next."
        )

    try:
        audio_url = tts_synthesizer(teacher_text, resolved_target_lang, voice_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc

    if user_id is not None:
        prompt_tokens = estimate_text_tokens(transcript)
        output_tokens = estimate_text_tokens(teacher_text)
        record_usage_event(
            db,
            user_id=user_id,
            scope="voice_teacher",
            model=settings.openai_voice_model,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
        )
        db.commit()

    return VoiceMessageResponse(
        transcript=transcript,
        teacher_text=teacher_text,
        audio_url=audio_url,
        pronunciation_feedback=build_pronunciation_feedback(transcript),
        pronunciation_rubric=build_pronunciation_rubric(transcript),
    )


@router.get("/progress", response_model=VoiceProgressResponse)
def voice_progress(user_id: int, db: Session = Depends(get_db)) -> VoiceProgressResponse:
    snapshots = db.scalars(
        select(SkillSnapshot).where(SkillSnapshot.user_id == user_id).order_by(SkillSnapshot.created_at.asc())
    ).all()
    points: list[VoiceProgressPoint] = []
    for snapshot in snapshots[-12:]:
        points.append(
            VoiceProgressPoint(
                date=(snapshot.created_at.astimezone(UTC).date().isoformat() if snapshot.created_at else "unknown"),
                speaking_score=round(float(snapshot.speaking), 2),
            )
        )

    trend = "stable"
    if len(points) >= 2:
        delta = points[-1].speaking_score - points[0].speaking_score
        if delta > 3:
            trend = "improving"
        elif delta < -3:
            trend = "declining"

    cutoff = datetime.now(UTC) - timedelta(days=7)
    pron_mistakes = db.scalars(
        select(Mistake)
        .where(Mistake.user_id == user_id, Mistake.category == "pronunciation", Mistake.created_at >= cutoff)
    ).all()
    pronunciation_mistakes_7d = len(pron_mistakes)
    recommendation = (
        "Run 3 short pronunciation retries on the same phrase this week."
        if pronunciation_mistakes_7d > 0
        else "Keep one weekly pronunciation checkpoint to maintain clarity."
    )

    return VoiceProgressResponse(
        user_id=user_id,
        trend=trend,
        points=points,
        pronunciation_mistakes_7d=pronunciation_mistakes_7d,
        recommendation=recommendation,
    )
