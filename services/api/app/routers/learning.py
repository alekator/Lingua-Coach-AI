from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatSession, LearnerProfile, Message, Mistake, SkillSnapshot, SrsState, User, VocabItem
from app.schemas.learning import (
    CoachSessionTodayResponse,
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
    ScenarioScriptResponse,
    ScenarioTurnRequest,
    ScenarioTurnResponse,
    ScenariosResponse,
    TranslateVoiceResponse,
)
from app.services.learning import (
    build_adaptive_plan,
    build_today_session_steps,
    default_scenarios,
    evaluate_scenario_turn,
    generate_exercises,
    grade_exercises,
    scenario_scripts,
)
from app.services.progress import compute_streak_days
from app.services.srs import utcnow
from app.services.translate import TranslatorFn, TtsSynthesizerFn
from app.services.voice import AsrTranscriberFn

router = APIRouter(tags=["learning"])


def _to_utc_date(dt: datetime) -> datetime.date:
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(UTC).date()


def _to_utc_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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
    score, max_score, details, rubric = grade_exercises(payload.answers, payload.expected)
    return ExercisesGradeResponse(score=score, max_score=max_score, details=details, rubric=rubric)


@router.get("/plan/today", response_model=PlanTodayResponse)
def plan_today(
    user_id: int,
    time_budget_minutes: int = 15,
    db: Session = Depends(get_db),
) -> PlanTodayResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    snapshot = db.scalar(
        select(SkillSnapshot).where(SkillSnapshot.user_id == user_id).order_by(SkillSnapshot.created_at.desc())
    )

    recent_mistakes = db.scalars(
        select(Mistake)
        .where(Mistake.user_id == user_id)
        .order_by(Mistake.created_at.desc())
        .limit(40)
    ).all()
    due_vocab_count = db.scalar(
        select(func.count(SrsState.vocab_item_id))
        .select_from(SrsState)
        .join(VocabItem, VocabItem.id == SrsState.vocab_item_id)
        .where(VocabItem.user_id == user_id, SrsState.due_at <= utcnow())
    )
    recent_user_messages_count = db.scalar(
        select(func.count(Message.id))
        .select_from(Message)
        .join(ChatSession, ChatSession.id == Message.session_id)
        .where(ChatSession.user_id == user_id, Message.role == "user")
    )
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    active_dates = sorted({_to_utc_date(s.started_at) for s in sessions if s.started_at})
    streak_days = compute_streak_days(active_dates)
    cutoff = datetime.now(UTC) - timedelta(days=7)
    weekly_sessions = len([s for s in sessions if s.started_at and _to_utc_datetime(s.started_at) >= cutoff])

    weakest_skill: str | None = None
    weakest_skill_score: float | None = None
    if snapshot:
        skill_values = {
            "speaking": snapshot.speaking,
            "listening": snapshot.listening,
            "grammar": snapshot.grammar,
            "vocab": snapshot.vocab,
            "reading": snapshot.reading,
            "writing": snapshot.writing,
        }
        weakest_skill, weakest_skill_score = min(skill_values.items(), key=lambda item: item[1])

    focus, tasks, adaptation_notes = build_adaptive_plan(
        goal=profile.goal if profile else None,
        time_budget_minutes=time_budget_minutes,
        recent_mistake_categories=[m.category for m in recent_mistakes],
        due_vocab_count=int(due_vocab_count or 0),
        recent_user_messages_count=int(recent_user_messages_count or 0),
        streak_days=streak_days,
        weekly_sessions=weekly_sessions,
        weakest_skill=weakest_skill,
        weakest_skill_score=weakest_skill_score,
    )

    return PlanTodayResponse(
        user_id=user_id,
        time_budget_minutes=time_budget_minutes,
        focus=focus,
        tasks=tasks,
        adaptation_notes=adaptation_notes,
    )


@router.get("/coach/session/today", response_model=CoachSessionTodayResponse)
def coach_session_today(
    user_id: int,
    time_budget_minutes: int = 15,
    db: Session = Depends(get_db),
) -> CoachSessionTodayResponse:
    plan = plan_today(user_id=user_id, time_budget_minutes=time_budget_minutes, db=db)
    return CoachSessionTodayResponse(
        user_id=plan.user_id,
        time_budget_minutes=plan.time_budget_minutes,
        focus=plan.focus,
        steps=build_today_session_steps(plan.focus, plan.time_budget_minutes),
    )


@router.get("/scenarios", response_model=ScenariosResponse)
def scenarios() -> ScenariosResponse:
    return ScenariosResponse(items=default_scenarios())


@router.get("/scenarios/script", response_model=ScenarioScriptResponse)
def scenarios_script(scenario_id: str) -> ScenarioScriptResponse:
    scenario_map = {item.id: item for item in default_scenarios()}
    scenario = scenario_map.get(scenario_id)
    scripts = scenario_scripts()
    steps = scripts.get(scenario_id)
    if not scenario or not steps:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return ScenarioScriptResponse(
        scenario_id=scenario_id,
        title=scenario.title,
        description=scenario.description,
        steps=steps,
    )


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


@router.post("/scenarios/turn", response_model=ScenarioTurnResponse)
def scenarios_turn(payload: ScenarioTurnRequest) -> ScenarioTurnResponse:
    scripts = scenario_scripts()
    steps = scripts.get(payload.scenario_id)
    if not steps:
        raise HTTPException(status_code=404, detail="Scenario not found")
    step_index = next((idx for idx, s in enumerate(steps) if s.id == payload.step_id), -1)
    if step_index < 0:
        raise HTTPException(status_code=404, detail="Scenario step not found")

    current = steps[step_index]
    score, max_score, feedback = evaluate_scenario_turn(
        expected_keywords=current.expected_keywords,
        user_text=payload.user_text,
    )
    next_step = steps[step_index + 1] if step_index + 1 < len(steps) else None
    done = next_step is None
    suggested_reply = None if score >= max_score else f"Try again using: {', '.join(current.expected_keywords[:2])}"

    return ScenarioTurnResponse(
        scenario_id=payload.scenario_id,
        step_id=current.id,
        score=score,
        max_score=max_score,
        feedback=feedback,
        next_step_id=None if done else next_step.id,
        next_prompt=None if done else next_step.coach_prompt,
        done=done,
        suggested_reply=suggested_reply,
    )
