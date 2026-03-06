from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    ChatSession,
    Homework,
    LearnerProfile,
    Message,
    Mistake,
    SessionStepProgress,
    SkillSnapshot,
    SrsState,
    User,
    VocabItem,
)
from app.schemas.learning import (
    CoachDailyChallengeResponse,
    CoachErrorBankItem,
    CoachErrorBankResponse,
    CoachNextAction,
    CoachNextActionsResponse,
    CoachSessionProgressResponse,
    CoachSessionProgressUpsertRequest,
    CoachSessionStepProgressItem,
    CoachReactivationResponse,
    CoachRoadmapItem,
    CoachRoadmapResponse,
    CoachSessionTodayResponse,
    CoachTrajectoryMilestone,
    CoachTrajectoryResponse,
    ExercisesGenerateRequest,
    ExercisesGenerateResponse,
    ExercisesGradeRequest,
    ExercisesGradeResponse,
    GrammarAnalyzeRequest,
    GrammarAnalyzeResponse,
    GrammarError,
    PlanTodayResponse,
    OutcomePackItem,
    OutcomePacksResponse,
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
    build_suggested_reply,
    default_scenarios,
    evaluate_scenario_turn,
    generate_exercises,
    grade_exercises,
    script_for_level,
    scenario_scripts,
)
from app.services.progress import compute_streak_days
from app.services.srs import utcnow
from app.services.translate import TranslatorFn, TtsSynthesizerFn
from app.services.voice import AsrTranscriberFn

router = APIRouter(tags=["learning"])
CEFR_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
SCENARIO_REQUIRED_LEVEL: dict[str, str] = {
    "travel-hotel": "A1",
    "coffee-shop": "A1",
    "daily-shopping": "A1",
    "daily-directions": "A1",
    "daily-neighbor": "A2",
    "daily-phone-call": "A2",
    "travel-restaurant": "A2",
    "airport-customs": "A2",
    "job-interview": "B1",
    "work-standup": "B1",
    "work-meeting": "B1",
    "work-feedback": "B1",
    "work-email": "B1",
    "relocation-rental": "B1",
    "relocation-bank": "B1",
    "relocation-clinic": "B1",
    "service-return": "B1",
    "service-support": "B1",
    "networking-event": "B2",
    "study-presentation": "B2",
    "study-storytelling": "B2",
    "study-debate": "B2",
    "travel-emergency": "B2",
}
LEVEL_SKILL_MIN_AVG = {"A1": 25.0, "A2": 35.0, "B1": 45.0, "B2": 58.0, "C1": 72.0, "C2": 85.0}


def _to_utc_date(dt: datetime) -> datetime.date:
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(UTC).date()


def _to_utc_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _reactivation_gap_days(sessions: list[ChatSession]) -> int:
    active_dates = sorted({_to_utc_date(s.started_at) for s in sessions if s.started_at})
    if not active_dates:
        return 999
    last_active = active_dates[-1]
    today = datetime.now(UTC).date()
    return max(0, (today - last_active).days)


def _snapshot_avg(snapshot: SkillSnapshot | None) -> float:
    if snapshot is None:
        return 0.0
    return float(
        (
            snapshot.speaking
            + snapshot.listening
            + snapshot.grammar
            + snapshot.vocab
            + snapshot.reading
            + snapshot.writing
        )
        / 6.0
    )


def _score_to_cefr(score: float) -> str:
    if score < 25:
        return "A1"
    if score < 40:
        return "A2"
    if score < 55:
        return "B1"
    if score < 70:
        return "B2"
    if score < 85:
        return "C1"
    return "C2"


def _mastery_context(user_id: int, db: Session) -> tuple[str, float]:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    profile_level = (profile.level if profile else "A1").upper()
    snapshot = db.scalar(
        select(SkillSnapshot).where(SkillSnapshot.user_id == user_id).order_by(SkillSnapshot.created_at.desc())
    )
    avg = _snapshot_avg(snapshot)
    estimated_level = _score_to_cefr(avg)
    effective_level = profile_level
    if CEFR_RANK.get(estimated_level, 1) > CEFR_RANK.get(profile_level, 1):
        effective_level = estimated_level
    return effective_level, avg


def _scenario_gate(user_id: int | None, scenario_id: str, db: Session) -> tuple[bool, str | None, str]:
    required = SCENARIO_REQUIRED_LEVEL.get(scenario_id, "A1")
    if user_id is None:
        return True, None, required
    effective_level, avg = _mastery_context(user_id=user_id, db=db)
    required_rank = CEFR_RANK.get(required, 1)
    current_rank = CEFR_RANK.get(effective_level, 1)
    skill_min = LEVEL_SKILL_MIN_AVG.get(required, 25.0)
    if current_rank >= required_rank and avg >= skill_min:
        return True, None, required
    reason = (
        f"Unlock at {required}+ with avg skill >= {int(skill_min)} "
        f"(now {effective_level}, avg {int(round(avg))})."
    )
    return False, reason, required


def _build_error_bank_items(db: Session, user_id: int, limit: int = 5) -> list[CoachErrorBankItem]:
    mistakes = db.scalars(
        select(Mistake)
        .where(Mistake.user_id == user_id)
        .order_by(Mistake.created_at.desc())
        .limit(150)
    ).all()
    if not mistakes:
        return []

    grouped: dict[str, dict[str, object]] = {}
    for item in mistakes:
        category = (item.category or "").strip().lower() or "general"
        if category not in grouped:
            grouped[category] = {
                "occurrences": 0,
                "last_seen_at": item.created_at,
                "latest_bad": item.bad,
                "latest_good": item.good,
                "latest_explanation": item.explanation,
            }
        grouped_item = grouped[category]
        grouped_item["occurrences"] = int(grouped_item["occurrences"]) + 1
        current_seen = grouped_item["last_seen_at"]
        if isinstance(current_seen, datetime):
            if item.created_at > current_seen:
                grouped_item["last_seen_at"] = item.created_at
                grouped_item["latest_bad"] = item.bad
                grouped_item["latest_good"] = item.good
                grouped_item["latest_explanation"] = item.explanation

    ranked = sorted(
        grouped.items(),
        key=lambda kv: (-int(kv[1]["occurrences"]), -int(_to_utc_datetime(kv[1]["last_seen_at"]).timestamp())),
    )
    items: list[CoachErrorBankItem] = []
    for category, data in ranked[: max(1, min(20, limit))]:
        latest_bad = str(data["latest_bad"]).strip()
        latest_good = str(data["latest_good"]).strip()
        latest_explanation = (
            str(data["latest_explanation"]).strip() if data["latest_explanation"] is not None else None
        )
        drill = f"Rewrite 3 short lines fixing '{latest_bad}' -> '{latest_good}'."
        if latest_explanation:
            drill = f"{drill} Focus: {latest_explanation}"
        items.append(
            CoachErrorBankItem(
                category=category,
                occurrences=int(data["occurrences"]),
                latest_bad=latest_bad,
                latest_good=latest_good,
                latest_explanation=latest_explanation,
                last_seen_at=_to_utc_datetime(data["last_seen_at"]),
                drill_prompt=drill,
                suggested_route="/app/exercises",
            )
        )
    return items


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


def _build_session_progress_response(
    user_id: int,
    time_budget_minutes: int,
    db: Session,
) -> CoachSessionProgressResponse:
    plan = plan_today(user_id=user_id, time_budget_minutes=time_budget_minutes, db=db)
    steps = build_today_session_steps(plan.focus, plan.time_budget_minutes)
    today = datetime.now(UTC).date()
    rows = db.scalars(
        select(SessionStepProgress).where(
            SessionStepProgress.user_id == user_id,
            SessionStepProgress.session_date == today,
        )
    ).all()
    status_by_step = {row.step_id: row for row in rows}
    items: list[CoachSessionStepProgressItem] = []
    completed_steps = 0
    for step in steps:
        row = status_by_step.get(step.id)
        status = "pending"
        started_at = None
        completed_at = None
        if row is not None:
            status = row.status if row.status in {"pending", "in_progress", "completed"} else "pending"
            started_at = row.started_at
            completed_at = row.completed_at
        if status == "completed":
            completed_steps += 1
        items.append(
            CoachSessionStepProgressItem(
                step_id=step.id,
                title=step.title,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
            )
        )
    total_steps = len(items)
    completion_percent = int(round((completed_steps / max(1, total_steps)) * 100))
    return CoachSessionProgressResponse(
        user_id=user_id,
        session_date=today,
        total_steps=total_steps,
        completed_steps=completed_steps,
        completion_percent=completion_percent,
        items=items,
    )


@router.get("/coach/session/progress", response_model=CoachSessionProgressResponse)
def coach_session_progress(
    user_id: int,
    time_budget_minutes: int = 15,
    db: Session = Depends(get_db),
) -> CoachSessionProgressResponse:
    return _build_session_progress_response(user_id=user_id, time_budget_minutes=time_budget_minutes, db=db)


@router.post("/coach/session/progress", response_model=CoachSessionProgressResponse)
def coach_session_progress_upsert(
    payload: CoachSessionProgressUpsertRequest,
    db: Session = Depends(get_db),
) -> CoachSessionProgressResponse:
    plan = plan_today(user_id=payload.user_id, time_budget_minutes=payload.time_budget_minutes, db=db)
    valid_step_ids = {step.id for step in build_today_session_steps(plan.focus, plan.time_budget_minutes)}
    if payload.step_id not in valid_step_ids:
        raise HTTPException(status_code=400, detail="Invalid step_id for today's session")

    now = datetime.now(UTC)
    today = now.date()
    row = db.scalar(
        select(SessionStepProgress).where(
            SessionStepProgress.user_id == payload.user_id,
            SessionStepProgress.session_date == today,
            SessionStepProgress.step_id == payload.step_id,
        )
    )
    if row is None:
        row = SessionStepProgress(
            user_id=payload.user_id,
            session_date=today,
            step_id=payload.step_id,
            status="pending",
        )
        db.add(row)
        db.flush()

    if payload.status == "in_progress":
        row.status = "in_progress"
        if row.started_at is None:
            row.started_at = now
        row.completed_at = None
    elif payload.status == "completed":
        row.status = "completed"
        if row.started_at is None:
            row.started_at = now
        row.completed_at = now
    else:
        row.status = "pending"
        row.completed_at = None

    db.commit()
    return _build_session_progress_response(
        user_id=payload.user_id,
        time_budget_minutes=payload.time_budget_minutes,
        db=db,
    )


@router.get("/coach/error-bank", response_model=CoachErrorBankResponse)
def coach_error_bank(user_id: int, limit: int = 5, db: Session = Depends(get_db)) -> CoachErrorBankResponse:
    safe_limit = max(1, min(20, limit))
    return CoachErrorBankResponse(
        user_id=user_id,
        items=_build_error_bank_items(db=db, user_id=user_id, limit=safe_limit),
    )


@router.get("/coach/next-actions", response_model=CoachNextActionsResponse)
def coach_next_actions(user_id: int, db: Session = Depends(get_db)) -> CoachNextActionsResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    preferences = (profile.preferences if profile else {}) or {}
    weekly_goal_minutes = int(preferences.get("weekly_goal_minutes", 90))
    weekly_goal_minutes = max(30, min(2000, weekly_goal_minutes))

    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    cutoff = datetime.now(UTC) - timedelta(days=7)
    weekly_sessions = [s for s in sessions if s.started_at and _to_utc_datetime(s.started_at) >= cutoff]
    weekly_minutes = len(weekly_sessions) * 8
    remaining_minutes = max(0, weekly_goal_minutes - weekly_minutes)

    due_vocab_count = int(
        db.scalar(
            select(func.count(SrsState.vocab_item_id))
            .select_from(SrsState)
            .join(VocabItem, VocabItem.id == SrsState.vocab_item_id)
            .where(VocabItem.user_id == user_id, SrsState.due_at <= utcnow())
        )
        or 0
    )
    auto_drill_count = int(
        db.scalar(
            select(func.count(Homework.id))
            .select_from(Homework)
            .where(
                Homework.user_id == user_id,
                Homework.status == "assigned",
                Homework.title.like("Auto Drill:%"),
            )
        )
        or 0
    )
    weak_top = db.scalars(
        select(Mistake.category)
        .where(Mistake.user_id == user_id)
        .order_by(Mistake.created_at.desc())
        .limit(50)
    ).all()
    top_weak = ""
    if weak_top:
        counts: dict[str, int] = {}
        for category in weak_top:
            if not category:
                continue
            counts[category] = counts.get(category, 0) + 1
        if counts:
            top_weak = max(counts.items(), key=lambda item: item[1])[0]

    items: list[CoachNextAction] = []
    if remaining_minutes > 0:
        items.append(
            CoachNextAction(
                id="weekly-goal",
                title=f"Complete {remaining_minutes} more weekly minutes",
                reason="Weekly target not completed yet.",
                route="/app/session",
                priority=1,
                quick_mode_minutes=10,
            )
        )
    if auto_drill_count > 0:
        items.append(
            CoachNextAction(
                id="auto-drills",
                title=f"Finish {auto_drill_count} personalized auto drills",
                reason="These drills come from your latest correction patterns.",
                route="/app/homework",
                priority=2,
                quick_mode_minutes=5,
            )
        )
    if due_vocab_count > 0:
        items.append(
            CoachNextAction(
                id="vocab-due",
                title=f"Review {due_vocab_count} due vocab cards",
                reason="Spaced repetition is due now.",
                route="/app/vocab",
                priority=3,
                quick_mode_minutes=5,
            )
        )
    if top_weak:
        encoded_topic = quote(top_weak, safe="")
        items.append(
            CoachNextAction(
                id="weak-area",
                title=f"Run a targeted {top_weak} drill",
                reason="Most frequent recent weak area.",
                route=f"/app/exercises?topic={encoded_topic}",
                priority=4,
                quick_mode_minutes=5,
            )
        )
    error_bank = _build_error_bank_items(db=db, user_id=user_id, limit=1)
    if error_bank:
        bank_top = error_bank[0]
        encoded_topic = quote(bank_top.category, safe="")
        items.append(
            CoachNextAction(
                id="error-bank-top",
                title=f"Fix recurring {bank_top.category} pattern ({bank_top.occurrences}x)",
                reason=bank_top.drill_prompt,
                route=f"{bank_top.suggested_route}?topic={encoded_topic}&source=error-bank",
                priority=2,
                quick_mode_minutes=5,
            )
        )
    if not items:
        items.append(
            CoachNextAction(
                id="keep-momentum",
                title="Keep momentum with one short coach chat",
                reason="No urgent pending actions detected.",
                route="/app/chat",
                priority=1,
                quick_mode_minutes=5,
            )
        )

    return CoachNextActionsResponse(user_id=user_id, items=sorted(items, key=lambda item: item.priority)[:4])


@router.get("/coach/daily-challenge", response_model=CoachDailyChallengeResponse)
def coach_daily_challenge(user_id: int, db: Session = Depends(get_db)) -> CoachDailyChallengeResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    goal = (profile.goal if profile and profile.goal else "general communication").strip()

    due_vocab_count = int(
        db.scalar(
            select(func.count(SrsState.vocab_item_id))
            .select_from(SrsState)
            .join(VocabItem, VocabItem.id == SrsState.vocab_item_id)
            .where(VocabItem.user_id == user_id, SrsState.due_at <= utcnow())
        )
        or 0
    )
    top_weak = db.scalars(
        select(Mistake.category)
        .where(Mistake.user_id == user_id)
        .order_by(Mistake.created_at.desc())
        .limit(30)
    ).all()
    weak_topic = next((category for category in top_weak if category), "grammar")

    if due_vocab_count > 0:
        return CoachDailyChallengeResponse(
            user_id=user_id,
            title="Daily Challenge: Vocab Sprint",
            reason="You have due cards ready for high-impact recall.",
            task=f"Review {min(5, due_vocab_count)} due vocab cards and use one in a short sentence.",
            route="/app/vocab",
            estimated_minutes=5,
        )

    return CoachDailyChallengeResponse(
        user_id=user_id,
        title="Daily Challenge: One Clear Step",
        reason=f"Fast progress for your {goal} goal with minimal friction.",
        task=f"Write one short message focused on {weak_topic}, then apply one correction.",
        route="/app/chat",
        estimated_minutes=5,
    )


@router.get("/coach/trajectory", response_model=CoachTrajectoryResponse)
def coach_trajectory(
    user_id: int,
    horizon_days: int = 30,
    db: Session = Depends(get_db),
) -> CoachTrajectoryResponse:
    horizon = 30 if horizon_days <= 30 else 60 if horizon_days <= 60 else 90
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    session_count = len(sessions)
    level = (profile.level if profile else "A1").upper()
    goal = (profile.goal if profile and profile.goal else "general communication")

    if session_count < 5:
        current_phase = "foundation"
    elif session_count < 15:
        current_phase = "consolidation"
    else:
        current_phase = "expansion"

    retake_recommended = session_count >= 12 or horizon == 90

    milestones = [
        CoachTrajectoryMilestone(day=7, title="Consistency", target="Reach at least 4 short sessions."),
        CoachTrajectoryMilestone(day=14, title="Correction Loop", target="Apply top 2 correction patterns reliably."),
        CoachTrajectoryMilestone(day=30, title="Functional Output", target=f"Handle one full {goal} scenario confidently."),
    ]
    if horizon >= 60:
        milestones.append(
            CoachTrajectoryMilestone(day=60, title="Fluency Build", target="Sustain multi-turn responses with fewer pauses.")
        )
    if horizon >= 90:
        milestones.append(
            CoachTrajectoryMilestone(day=90, title="Reassessment", target=f"Run mini placement retake from level {level}.")
        )

    return CoachTrajectoryResponse(
        user_id=user_id,
        horizon_days=horizon,
        current_phase=current_phase,
        retake_recommended=retake_recommended,
        milestones=milestones,
    )


@router.get("/coach/roadmap", response_model=CoachRoadmapResponse)
def coach_roadmap(user_id: int, db: Session = Depends(get_db)) -> CoachRoadmapResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    goal = (profile.goal if profile and profile.goal else "general communication")
    weak_top = db.scalars(
        select(Mistake.category)
        .where(Mistake.user_id == user_id)
        .order_by(Mistake.created_at.desc())
        .limit(50)
    ).all()
    top_weak = next((category for category in weak_top if category), "grammar")

    items = [
        CoachRoadmapItem(
            id="roadmap-chat-loop",
            title="Correction-to-production loop",
            reason=f"Your current weak area is {top_weak}; chat loop gives fast transfer to output.",
            route="/app/chat",
            priority=1,
        ),
        CoachRoadmapItem(
            id="roadmap-drills",
            title=f"Targeted {top_weak} drills",
            reason="Convert recurring mistakes into stable patterns with short focused drills.",
            route="/app/exercises",
            priority=2,
        ),
        CoachRoadmapItem(
            id="roadmap-scenario",
            title=f"{goal.title()} scenario rehearsal",
            reason="Apply corrected language in realistic multi-step context.",
            route="/app/scenarios",
            priority=3,
        ),
        CoachRoadmapItem(
            id="roadmap-review",
            title="Spaced review anchor",
            reason="Keep retention stable while complexity grows.",
            route="/app/vocab",
            priority=4,
        ),
    ]
    return CoachRoadmapResponse(user_id=user_id, goal=goal, items=items)


@router.get("/coach/outcome-packs", response_model=OutcomePacksResponse)
def coach_outcome_packs(user_id: int, db: Session = Depends(get_db)) -> OutcomePacksResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    current_level = (profile.level if profile else "A1").upper()
    level_rank = CEFR_RANK.get(current_level, 1)
    weekly_sessions = len(
        [
            s
            for s in db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
            if s.started_at and _to_utc_datetime(s.started_at) >= (datetime.now(UTC) - timedelta(days=7))
        ]
    )

    packs = [
        ("job-pack", "Job Interview Pack", "B1", "/app/scenarios"),
        ("relocation-pack", "Relocation Essentials Pack", "A2", "/app/scenarios"),
        ("exam-pack", "Exam Readiness Pack", "B2", "/app/exercises"),
    ]
    items: list[OutcomePackItem] = []
    for pack_id, title, target_level, route in packs:
        target_rank = CEFR_RANK[target_level]
        missing: list[str] = []
        if level_rank < target_rank:
            missing.append(f"Level below target ({current_level} -> {target_level})")
        if weekly_sessions < 3:
            missing.append("Need at least 3 sessions this week")
        readiness = "ready" if not missing else "almost_ready" if len(missing) == 1 else "not_ready"
        items.append(
            OutcomePackItem(
                id=pack_id,
                title=title,
                target_level=target_level,
                readiness=readiness,
                missing_signals=missing,
                recommended_route=route,
            )
        )

    return OutcomePacksResponse(user_id=user_id, items=items)


@router.get("/coach/reactivation", response_model=CoachReactivationResponse)
def coach_reactivation(user_id: int, db: Session = Depends(get_db)) -> CoachReactivationResponse:
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    gap_days = _reactivation_gap_days(sessions)
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    goal = (profile.goal if profile and profile.goal else "general communication").strip()

    weak_top = db.scalars(
        select(Mistake.category)
        .where(Mistake.user_id == user_id)
        .order_by(Mistake.created_at.desc())
        .limit(30)
    ).all()
    weak_topic = next((category for category in weak_top if category), None)

    due_vocab_count = int(
        db.scalar(
            select(func.count(SrsState.vocab_item_id))
            .select_from(SrsState)
            .join(VocabItem, VocabItem.id == SrsState.vocab_item_id)
            .where(VocabItem.user_id == user_id, SrsState.due_at <= utcnow())
        )
        or 0
    )
    target_topic = weak_topic or "grammar"
    target_topic_encoded = quote(target_topic, safe="")
    cta_route = "/app/chat"
    tasks = [
        f"2 min: quick warmup in {target_topic} for your {goal} goal with one simple sentence.",
        "2 min: one short coach chat turn and apply one correction.",
        "1 min: close with one success line to lock momentum.",
    ]
    if due_vocab_count > 0:
        tasks[0] = f"2 min: review {min(due_vocab_count, 5)} due vocab cards for easy restart."
        cta_route = "/app/vocab"
    elif weak_topic:
        tasks[1] = f"2 min: one compact {weak_topic} drill and apply one correction."
        cta_route = f"/app/exercises?topic={target_topic_encoded}&source=reactivation"
    else:
        cta_route = "/app/chat"

    if gap_days < 2:
        return CoachReactivationResponse(
            user_id=user_id,
            eligible=False,
            gap_days=gap_days,
            weak_topic=weak_topic,
            title="No reactivation needed",
            tasks=[],
            cta_route="/app/session",
            note="You are active recently. Keep normal daily flow.",
        )

    return CoachReactivationResponse(
        user_id=user_id,
        eligible=True,
        gap_days=gap_days,
        weak_topic=weak_topic,
        title=f"Easy return plan after {gap_days} day break",
        tasks=tasks,
        cta_route=cta_route,
        note="Keep it light today. The goal is to restart momentum, not intensity.",
    )


@router.get("/scenarios", response_model=ScenariosResponse)
def scenarios(user_id: int | None = None, db: Session = Depends(get_db)) -> ScenariosResponse:
    scenario_items = []
    for item in default_scenarios():
        unlocked, reason, required = _scenario_gate(user_id=user_id, scenario_id=item.id, db=db)
        scenario_items.append(
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "required_level": required,
                "unlocked": unlocked,
                "gate_reason": reason,
            }
        )
    return ScenariosResponse(items=scenario_items)


@router.get("/scenarios/script", response_model=ScenarioScriptResponse)
def scenarios_script(scenario_id: str, user_id: int | None = None, db: Session = Depends(get_db)) -> ScenarioScriptResponse:
    scenario_map = {item.id: item for item in default_scenarios()}
    scenario = scenario_map.get(scenario_id)
    scripts = scenario_scripts()
    steps = scripts.get(scenario_id)
    if not scenario or not steps:
        raise HTTPException(status_code=404, detail="Scenario not found")
    level = "A2"
    if user_id is not None:
        profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
        if profile is not None:
            level = profile.level
    return ScenarioScriptResponse(
        scenario_id=scenario_id,
        title=scenario.title,
        description=scenario.description,
        steps=script_for_level(steps, level),
    )


@router.post("/scenarios/select", response_model=ScenarioSelectResponse)
def scenarios_select(
    payload: ScenarioSelectRequest,
    db: Session = Depends(get_db),
) -> ScenarioSelectResponse:
    scenario_ids = {item.id for item in default_scenarios()}
    if payload.scenario_id not in scenario_ids:
        raise HTTPException(status_code=404, detail="Scenario not found")
    unlocked, reason, _required = _scenario_gate(user_id=payload.user_id, scenario_id=payload.scenario_id, db=db)
    if not unlocked:
        raise HTTPException(status_code=403, detail=reason or "Scenario is locked by mastery gate")

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
    suggested_reply = None if score >= max_score else build_suggested_reply(current.expected_keywords)

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
