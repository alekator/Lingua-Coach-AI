from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatSession, Homework, LearnerProfile, Message, Mistake, SkillSnapshot, User, VocabItem
from app.schemas.chat import (
    ChatEndRequest,
    ChatEndResponse,
    Correction,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatStartRequest,
    ChatStartResponse,
)
from app.config import settings
from app.services.placement import utcnow
from app.services.teacher import (
    TeacherResponder,
    build_resilient_teacher_fallback,
    build_teacher_payload,
    default_teacher_responder,
)
from app.services.mastery import next_skill_snapshot_from_chat
from app.services.usage_budget import estimate_text_tokens, get_usage_budget_snapshot, record_usage_event

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_or_create_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user:
        return user
    user = User(id=user_id)
    db.add(user)
    db.flush()
    return user


def _upsert_auto_drill_homework(db: Session, user_id: int, corrections: list[Correction]) -> None:
    if not corrections:
        return

    primary_category = corrections[0].type or "general"
    title = f"Auto Drill: {primary_category}"
    existing = db.scalars(
        select(Homework)
        .where(Homework.user_id == user_id, Homework.status == "assigned", Homework.title == title)
        .order_by(Homework.created_at.desc())
    ).first()

    new_tasks: list[dict[str, str]] = []
    for correction in corrections[:3]:
        prompt = f"Fix and rewrite: {correction.bad}"
        task = {
            "id": f"auto-{correction.type}-{len(correction.bad)}-{len(correction.good)}",
            "type": "rewrite",
            "prompt": prompt,
            "expected_answer": correction.good,
            "hint": correction.explanation or "Use the corrected form exactly once.",
        }
        new_tasks.append(task)

    if existing is None:
        db.add(
            Homework(
                user_id=user_id,
                title=title,
                tasks=new_tasks,
                status="assigned",
            )
        )
        return

    current_tasks = list(existing.tasks or [])
    seen_prompts = {str(item.get("prompt", "")) for item in current_tasks if isinstance(item, dict)}
    for task in new_tasks:
        if task["prompt"] not in seen_prompts:
            current_tasks.append(task)
    existing.tasks = current_tasks[:8]


@router.post("/start", response_model=ChatStartResponse)
def chat_start(payload: ChatStartRequest, db: Session = Depends(get_db)) -> ChatStartResponse:
    _get_or_create_user(db, payload.user_id)
    session = ChatSession(user_id=payload.user_id, mode=payload.mode)
    db.add(session)
    db.commit()
    db.refresh(session)
    return ChatStartResponse(session_id=session.id, mode=session.mode, status="started")


@router.post("/message", response_model=ChatMessageResponse)
def chat_message(
    payload: ChatMessageRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    session = db.get(ChatSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if session.ended_at is not None:
        raise HTTPException(status_code=409, detail="Chat session already ended")

    history = db.scalars(
        select(Message).where(Message.session_id == session.id).order_by(Message.created_at.asc())
    ).all()
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == session.user_id))
    recent_mistakes = db.scalars(
        select(Mistake)
        .where(Mistake.user_id == session.user_id)
        .order_by(Mistake.created_at.desc())
        .limit(20)
    ).all()
    active_vocab = db.scalars(
        select(VocabItem)
        .where(VocabItem.user_id == session.user_id)
        .order_by(VocabItem.created_at.desc())
        .limit(40)
    ).all()

    db.add(Message(session_id=session.id, role="user", text=payload.text))

    budget = get_usage_budget_snapshot(db, session.user_id)
    if budget.blocked:
        teacher_output = build_resilient_teacher_fallback(
            {"user_input": payload.text, "learner_profile": {"level": profile.level if profile else "A1"}},
            reason="usage budget exceeded",
        )
        teacher_output.assistant_text = (
            "Budget cap reached for this period. "
            "Switched to lightweight coach mode: no paid model calls.\n\n"
            + teacher_output.assistant_text
        )
        db.add(Message(session_id=session.id, role="assistant", text=teacher_output.assistant_text))
        db.commit()
        return teacher_output

    teacher_responder: TeacherResponder = getattr(
        request.app.state, "teacher_responder", default_teacher_responder
    )
    teacher_payload = build_teacher_payload(
        profile,
        session.mode,
        payload.text,
        history,
        recent_mistakes=recent_mistakes,
        active_vocab=active_vocab,
    )

    try:
        teacher_output = teacher_responder(teacher_payload)
    except Exception as exc:
        teacher_output = build_resilient_teacher_fallback(
            teacher_payload,
            reason=f"teacher call failed: {exc}",
        )

    db.add(Message(session_id=session.id, role="assistant", text=teacher_output.assistant_text))
    prompt_tokens = estimate_text_tokens(payload.text)
    output_tokens = estimate_text_tokens(teacher_output.assistant_text)
    record_usage_event(
        db,
        user_id=session.user_id,
        scope="chat_teacher",
        model=settings.openai_chat_model,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
    )

    for correction in teacher_output.corrections:
        db.add(
            Mistake(
                user_id=session.user_id,
                category=correction.type,
                bad=correction.bad,
                good=correction.good,
                explanation=correction.explanation,
            )
        )

    for word in teacher_output.new_words:
        db.add(
            VocabItem(
                user_id=session.user_id,
                word=word.word,
                translation=word.translation,
                example=word.example,
                phonetics=word.phonetics,
            )
        )

    _upsert_auto_drill_homework(db, session.user_id, teacher_output.corrections)

    latest_snapshot = db.scalars(
        select(SkillSnapshot)
        .where(SkillSnapshot.user_id == session.user_id)
        .order_by(SkillSnapshot.created_at.desc())
    ).first()
    rubric_score = teacher_output.rubric.overall_score if teacher_output.rubric else None
    next_snapshot = next_skill_snapshot_from_chat(
        latest_snapshot,
        teacher_output.corrections,
        rubric_score,
    )
    db.add(SkillSnapshot(user_id=session.user_id, **next_snapshot))

    db.commit()
    return teacher_output


@router.post("/end", response_model=ChatEndResponse)
def chat_end(payload: ChatEndRequest, db: Session = Depends(get_db)) -> ChatEndResponse:
    session = db.get(ChatSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if session.ended_at is None:
        session.ended_at = utcnow()
        db.commit()
    return ChatEndResponse(session_id=session.id, status="ended")
