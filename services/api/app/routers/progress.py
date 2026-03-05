from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatSession, LearnerProfile, Message, Mistake, SkillSnapshot, SrsState, User, VocabItem
from app.schemas.progress import (
    ProgressJournalEntry,
    ProgressJournalResponse,
    ProgressSkillMapResponse,
    ProgressStreakResponse,
    ProgressSummaryResponse,
    WeeklyGoalResponse,
    WeeklyGoalSetRequest,
)
from app.services.progress import compute_streak_days

router = APIRouter(prefix="/progress", tags=["progress"])
DEFAULT_WEEKLY_GOAL_MINUTES = 90


def _to_utc_date(dt: datetime) -> datetime.date:
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(UTC).date()


def _to_utc_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _get_weekly_sessions(user_id: int, db: Session) -> list[ChatSession]:
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    cutoff = datetime.now(UTC) - timedelta(days=7)
    return [s for s in sessions if s.started_at and _to_utc_datetime(s.started_at) >= cutoff]


def _read_weekly_goal_target(profile: LearnerProfile | None) -> int:
    if not profile:
        return DEFAULT_WEEKLY_GOAL_MINUTES
    raw = (profile.preferences or {}).get("weekly_goal_minutes")
    if isinstance(raw, int) and raw >= 30:
        return raw
    return DEFAULT_WEEKLY_GOAL_MINUTES


def _get_or_create_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user:
        return user
    user = User(id=user_id)
    db.add(user)
    db.flush()
    return user


@router.get("/skill-map", response_model=ProgressSkillMapResponse)
def progress_skill_map(user_id: int, db: Session = Depends(get_db)) -> ProgressSkillMapResponse:
    snapshot = db.scalars(
        select(SkillSnapshot)
        .where(SkillSnapshot.user_id == user_id)
        .order_by(SkillSnapshot.created_at.desc())
    ).first()
    if not snapshot:
        return ProgressSkillMapResponse(
            speaking=0.0,
            listening=0.0,
            grammar=0.0,
            vocab=0.0,
            reading=0.0,
            writing=0.0,
        )
    return ProgressSkillMapResponse(
        speaking=snapshot.speaking,
        listening=snapshot.listening,
        grammar=snapshot.grammar,
        vocab=snapshot.vocab,
        reading=snapshot.reading,
        writing=snapshot.writing,
    )


@router.get("/streak", response_model=ProgressStreakResponse)
def progress_streak(user_id: int, db: Session = Depends(get_db)) -> ProgressStreakResponse:
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    active_dates = sorted({_to_utc_date(s.started_at) for s in sessions if s.started_at})
    streak = compute_streak_days(active_dates)
    return ProgressStreakResponse(streak_days=streak, active_dates=active_dates)


@router.get("/summary", response_model=ProgressSummaryResponse)
def progress_summary(user_id: int, db: Session = Depends(get_db)) -> ProgressSummaryResponse:
    words_learned = len(db.scalars(select(VocabItem).where(VocabItem.user_id == user_id)).all())
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    minutes_practiced = len(sessions) * 8

    active_dates = sorted({_to_utc_date(s.started_at) for s in sessions if s.started_at})
    streak = compute_streak_days(active_dates)

    skill = progress_skill_map(user_id=user_id, db=db)
    return ProgressSummaryResponse(
        streak_days=streak,
        minutes_practiced=minutes_practiced,
        words_learned=words_learned,
        speaking=skill.speaking,
        listening=skill.listening,
        grammar=skill.grammar,
        vocab=skill.vocab,
        reading=skill.reading,
        writing=skill.writing,
    )


@router.get("/journal", response_model=ProgressJournalResponse)
def progress_journal(user_id: int, db: Session = Depends(get_db)) -> ProgressJournalResponse:
    sessions = db.scalars(
        select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.started_at.desc())
    ).all()
    weekly_sessions = _get_weekly_sessions(user_id, db)

    message_counts = dict(
        db.execute(
            select(Message.session_id, func.count(Message.id))
            .join(ChatSession, ChatSession.id == Message.session_id)
            .where(ChatSession.user_id == user_id)
            .group_by(Message.session_id)
        ).all()
    )
    entries = [
        ProgressJournalEntry(
            session_id=s.id,
            started_at=_to_utc_date(s.started_at),
            mode=s.mode,
            messages_count=int(message_counts.get(s.id, 0)),
            completed=s.ended_at is not None,
        )
        for s in sessions[:15]
    ]

    mistakes = db.scalars(
        select(Mistake).where(Mistake.user_id == user_id).order_by(Mistake.created_at.desc()).limit(100)
    ).all()
    weak_areas = [name for name, _ in Counter(m.category for m in mistakes if m.category).most_common(3)]

    due_vocab_count = db.scalar(
        select(func.count(SrsState.vocab_item_id))
        .select_from(SrsState)
        .join(VocabItem, VocabItem.id == SrsState.vocab_item_id)
        .where(VocabItem.user_id == user_id, SrsState.due_at <= datetime.now(UTC))
    )
    next_actions: list[str] = []
    if due_vocab_count and due_vocab_count > 0:
        next_actions.append(f"Review due vocabulary cards ({int(due_vocab_count)}).")
    if weak_areas:
        next_actions.append(f"Run one targeted drill for: {weak_areas[0]}.")
    if len(weekly_sessions) < 3:
        next_actions.append("Add one short coach chat session today to keep momentum.")
    if not next_actions:
        next_actions.append("Great consistency. Keep the daily session cadence.")

    return ProgressJournalResponse(
        weekly_minutes=len(weekly_sessions) * 8,
        weekly_sessions=len(weekly_sessions),
        weak_areas=weak_areas,
        next_actions=next_actions,
        entries=entries,
    )


@router.get("/weekly-goal", response_model=WeeklyGoalResponse)
def progress_weekly_goal(user_id: int, db: Session = Depends(get_db)) -> WeeklyGoalResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    target_minutes = _read_weekly_goal_target(profile)
    completed_minutes = len(_get_weekly_sessions(user_id, db)) * 8
    remaining_minutes = max(0, target_minutes - completed_minutes)
    completion_percent = min(100, round((completed_minutes / max(1, target_minutes)) * 100))
    return WeeklyGoalResponse(
        user_id=user_id,
        target_minutes=target_minutes,
        completed_minutes=completed_minutes,
        remaining_minutes=remaining_minutes,
        completion_percent=completion_percent,
        is_completed=completed_minutes >= target_minutes,
    )


@router.post("/weekly-goal", response_model=WeeklyGoalResponse)
def progress_weekly_goal_set(payload: WeeklyGoalSetRequest, db: Session = Depends(get_db)) -> WeeklyGoalResponse:
    _get_or_create_user(db, payload.user_id)
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == payload.user_id))
    if profile is None:
        profile = LearnerProfile(
            user_id=payload.user_id,
            native_lang="ru",
            target_lang="en",
            level="A1",
            goal=None,
            preferences={"weekly_goal_minutes": payload.target_minutes},
        )
        db.add(profile)
    else:
        prefs = dict(profile.preferences or {})
        prefs["weekly_goal_minutes"] = payload.target_minutes
        profile.preferences = prefs
    db.commit()
    return progress_weekly_goal(user_id=payload.user_id, db=db)
