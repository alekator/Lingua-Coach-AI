from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Homework, HomeworkSubmission, SkillSnapshot, User
from app.schemas.homework import (
    HomeworkCreateRequest,
    HomeworkItem,
    HomeworkListResponse,
    HomeworkSubmitRequest,
    HomeworkSubmitResponse,
)

router = APIRouter(prefix="/homework", tags=["homework"])


def _get_or_create_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user:
        return user
    user = User(id=user_id)
    db.add(user)
    db.flush()
    return user


@router.post("/create", response_model=HomeworkItem)
def homework_create(payload: HomeworkCreateRequest, db: Session = Depends(get_db)) -> HomeworkItem:
    _get_or_create_user(db, payload.user_id)
    hw = Homework(
        user_id=payload.user_id,
        title=payload.title,
        tasks=payload.tasks,
        due_at=payload.due_at,
        status="assigned",
    )
    db.add(hw)
    db.commit()
    db.refresh(hw)
    return HomeworkItem.model_validate(hw, from_attributes=True)


@router.get("", response_model=HomeworkListResponse)
def homework_list(user_id: int, db: Session = Depends(get_db)) -> HomeworkListResponse:
    rows = db.scalars(select(Homework).where(Homework.user_id == user_id).order_by(Homework.created_at.desc())).all()
    return HomeworkListResponse(items=[HomeworkItem.model_validate(row, from_attributes=True) for row in rows])


@router.post("/submit", response_model=HomeworkSubmitResponse)
def homework_submit(payload: HomeworkSubmitRequest, db: Session = Depends(get_db)) -> HomeworkSubmitResponse:
    hw = db.get(Homework, payload.homework_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Homework not found")

    total_tasks = max(1, len(hw.tasks))
    answered = len(payload.answers)
    score = round(min(1.0, answered / total_tasks), 2)
    grade = {
        "score": score,
        "max_score": 1.0,
        "feedback": "Good progress. Continue daily practice.",
    }
    submission = HomeworkSubmission(homework_id=hw.id, answers=payload.answers, grade=grade)
    hw.status = "submitted"
    db.add(submission)

    last_snapshot = db.scalars(
        select(SkillSnapshot)
        .where(SkillSnapshot.user_id == hw.user_id)
        .order_by(SkillSnapshot.created_at.desc())
    ).first()
    base = last_snapshot.vocab if last_snapshot else 40.0
    delta = score * 5.0
    db.add(
        SkillSnapshot(
            user_id=hw.user_id,
            speaking=base,
            listening=base,
            grammar=min(100.0, base + delta),
            vocab=min(100.0, base + delta),
            reading=base,
            writing=min(100.0, base + delta / 2),
        )
    )
    db.commit()
    return HomeworkSubmitResponse(homework_id=hw.id, status=hw.status, grade=grade)
