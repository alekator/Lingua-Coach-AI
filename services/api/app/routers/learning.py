from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatSession, LearnerProfile, User
from app.schemas.learning import (
    ExercisesGenerateRequest,
    ExercisesGenerateResponse,
    ExercisesGradeRequest,
    ExercisesGradeResponse,
    GrammarAnalyzeRequest,
    GrammarAnalyzeResponse,
    GrammarError,
    PlanTodayResponse,
    ScenarioSelectRequest,
    ScenarioSelectResponse,
    ScenariosResponse,
    TranslateVoiceResponse,
)
from app.services.learning import default_scenarios, generate_exercises, grade_exercises
from app.services.translate import TranslatorFn, TtsSynthesizerFn
from app.services.voice import AsrTranscriberFn

router = APIRouter(tags=["learning"])


@router.post("/translate/voice", response_model=TranslateVoiceResponse)
async def translate_voice(
    request: Request,
    file: UploadFile = File(...),
    source_lang: str = Form(default="auto"),
    target_lang: str = Form(default="en"),
    language_hint: str = Form(default="auto"),
    voice_name: str = Form(default="alloy"),
) -> TranslateVoiceResponse:
    asr_transcriber: AsrTranscriberFn = request.app.state.asr_transcriber
    translator: TranslatorFn = request.app.state.translator
    tts_synthesizer: TtsSynthesizerFn = request.app.state.tts_synthesizer

    audio_bytes = await file.read()
    asr = asr_transcriber(
        audio_bytes,
        file.filename or "audio.webm",
        file.content_type or "audio/webm",
        language_hint,
    )
    transcript = asr["transcript"]
    translated = translator(transcript, source_lang, target_lang)
    audio_url = tts_synthesizer(translated, target_lang, voice_name)

    return TranslateVoiceResponse(
        transcript=transcript,
        translated_text=translated,
        audio_url=audio_url,
    )


@router.post("/grammar/analyze", response_model=GrammarAnalyzeResponse)
def grammar_analyze(payload: GrammarAnalyzeRequest) -> GrammarAnalyzeResponse:
    corrected = payload.text.replace("I goed", "I went").replace("I has", "I have")
    errors: list[GrammarError] = []
    if corrected != payload.text:
        errors.append(
            GrammarError(
                category="verb_form",
                bad=payload.text,
                good=corrected,
                explanation="Use correct irregular/auxiliary verb form.",
            )
        )
    return GrammarAnalyzeResponse(
        corrected_text=corrected,
        errors=errors,
        exercises=[
            "Rewrite two sentences using past tense.",
            "Write one sentence using present perfect.",
        ],
    )


@router.post("/exercises/generate", response_model=ExercisesGenerateResponse)
def exercises_generate(payload: ExercisesGenerateRequest) -> ExercisesGenerateResponse:
    return ExercisesGenerateResponse(
        items=generate_exercises(payload.exercise_type, payload.topic, payload.count)
    )


@router.post("/exercises/grade", response_model=ExercisesGradeResponse)
def exercises_grade(payload: ExercisesGradeRequest) -> ExercisesGradeResponse:
    score, max_score, details = grade_exercises(payload.answers, payload.expected)
    return ExercisesGradeResponse(score=score, max_score=max_score, details=details)


@router.get("/plan/today", response_model=PlanTodayResponse)
def plan_today(
    user_id: int,
    time_budget_minutes: int = 15,
    db: Session = Depends(get_db),
) -> PlanTodayResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))

    focus = ["grammar", "speaking", "vocab"]
    if profile and profile.goal:
        focus.insert(0, profile.goal)

    tasks = [
        f"5 min: quick review ({focus[0]})",
        "5 min: teacher chat with corrections",
        f"{max(2, time_budget_minutes - 10)} min: scenario practice",
    ]
    return PlanTodayResponse(
        user_id=user_id,
        time_budget_minutes=time_budget_minutes,
        focus=focus[:3],
        tasks=tasks,
    )


@router.get("/scenarios", response_model=ScenariosResponse)
def scenarios() -> ScenariosResponse:
    return ScenariosResponse(items=default_scenarios())


@router.post("/scenarios/select", response_model=ScenarioSelectResponse)
def scenarios_select(
    payload: ScenarioSelectRequest,
    db: Session = Depends(get_db),
) -> ScenarioSelectResponse:
    scenario_ids = {item.id for item in default_scenarios()}
    if payload.scenario_id not in scenario_ids:
        raise HTTPException(status_code=404, detail="Scenario not found")

    user = db.get(User, payload.user_id)
    if user is None:
        user = User(id=payload.user_id)
        db.add(user)
        db.flush()
    session = ChatSession(user_id=payload.user_id, mode=f"scenario:{payload.scenario_id}")
    db.add(session)
    db.commit()
    db.refresh(session)

    return ScenarioSelectResponse(session_id=session.id, mode=session.mode)
