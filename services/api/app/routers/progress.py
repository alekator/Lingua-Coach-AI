from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatSession, SkillSnapshot, VocabItem
from app.schemas.progress import (
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
