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
    HomeworkUpdateRequest,
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


def _to_homework_item(hw: Homework) -> HomeworkItem:
    latest_submission = hw.submissions[-1] if hw.submissions else None
    latest_score: float | None = None
    latest_feedback: str | None = None
    latest_answer_text: str | None = None
    if latest_submission:
        grade = latest_submission.grade or {}
        answers = latest_submission.answers or {}
        raw_score = grade.get("score")
        latest_score = float(raw_score) if isinstance(raw_score, (int, float)) else None
        latest_feedback = str(grade.get("feedback")) if grade.get("feedback") is not None else None
        if isinstance(answers, dict):
            response_text = answers.get("response")
            if response_text is None:
                first_answer = next(iter(answers.values()), None)
                latest_answer_text = str(first_answer) if first_answer is not None else None
            else:
                latest_answer_text = str(response_text)
    return HomeworkItem(
        id=hw.id,
        user_id=hw.user_id,
        title=hw.title,
        tasks=hw.tasks or [],
        status=hw.status,
        created_at=hw.created_at,
        due_at=hw.due_at,
        submission_count=len(hw.submissions),
        latest_score=latest_score,
        latest_feedback=latest_feedback,
        latest_answer_text=latest_answer_text,
    )


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
    return _to_homework_item(hw)


@router.get("", response_model=HomeworkListResponse)
def homework_list(user_id: int, db: Session = Depends(get_db)) -> HomeworkListResponse:
    rows = db.scalars(select(Homework).where(Homework.user_id == user_id).order_by(Homework.created_at.desc())).all()
    return HomeworkListResponse(items=[_to_homework_item(row) for row in rows])


@router.patch("/{homework_id}", response_model=HomeworkItem)
def homework_update(homework_id: int, payload: HomeworkUpdateRequest, db: Session = Depends(get_db)) -> HomeworkItem:
    hw = db.get(Homework, homework_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Homework not found")

    hw.title = payload.title
    hw.tasks = payload.tasks
    hw.due_at = payload.due_at
    hw.status = payload.status
    db.commit()
    db.refresh(hw)
    return _to_homework_item(hw)


@router.delete("/{homework_id}")
def homework_delete(homework_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    hw = db.get(Homework, homework_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Homework not found")
    db.delete(hw)
    db.commit()
    return {"deleted_homework_id": homework_id}


@router.post("/submit", response_model=HomeworkSubmitResponse)
def homework_submit(payload: HomeworkSubmitRequest, db: Session = Depends(get_db)) -> HomeworkSubmitResponse:
    hw = db.get(Homework, payload.homework_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Homework not found")

    total_tasks = max(1, len(hw.tasks))
    non_empty_answers = [value for value in payload.answers.values() if str(value).strip()]
    answered = len(non_empty_answers)
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
