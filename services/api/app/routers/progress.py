from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatSession, Message, Mistake, SkillSnapshot, SrsState, VocabItem
from app.schemas.progress import (
    ProgressJournalEntry,
    ProgressJournalResponse,
    ProgressSkillMapResponse,
    ProgressStreakResponse,
    ProgressSummaryResponse,
)
from app.services.progress import compute_streak_days

router = APIRouter(prefix="/progress", tags=["progress"])


def _to_utc_date(dt: datetime) -> datetime.date:
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(UTC).date()


def _to_utc_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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
    cutoff = datetime.now(UTC) - timedelta(days=7)
    weekly_sessions = [s for s in sessions if s.started_at and _to_utc_datetime(s.started_at) >= cutoff]

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
