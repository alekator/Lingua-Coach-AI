from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LearnerProfile, PlacementAnswer, PlacementSession, SkillSnapshot, User
from app.schemas.profile import (
    ProfileGetResponse,
    PlacementAnswerRequest,
    PlacementAnswerResponse,
    PlacementFinishRequest,
    PlacementFinishResponse,
    PlacementStartRequest,
    PlacementStartResponse,
    ProfileSetupRequest,
    ProfileSetupResponse,
)
from app.services.placement import (
    baseline_skill_map,
    build_placement_questions,
    score_answer,
    score_to_cefr,
    utcnow,
)
from app.services.workspaces import (
    LOCAL_OWNER_USER_ID,
    create_workspace,
    get_workspace_for_user,
    get_workspace_by_lang_pair,
    normalize_lang,
    set_active_workspace,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _get_or_create_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user:
        return user

    user = User(id=user_id)
    db.add(user)
    db.flush()
    return user


def _resolve_user_for_profile_setup(payload: ProfileSetupRequest, db: Session) -> tuple[int, str, str]:
    try:
        normalized_native = normalize_lang(payload.native_lang)
        normalized_target = normalize_lang(payload.target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if normalized_native == normalized_target:
        raise HTTPException(status_code=400, detail="Native and target language must be different")

    if payload.user_id != LOCAL_OWNER_USER_ID:
        workspace = get_workspace_for_user(db, payload.user_id)
        if workspace is not None:
            if workspace.native_lang != normalized_native or workspace.target_lang != normalized_target:
                raise HTTPException(
                    status_code=400,
                    detail="Workspace language pair mismatch for this user_id",
                )
            workspace.goal = payload.goal
            set_active_workspace(db, workspace)
            return payload.user_id, workspace.native_lang, workspace.target_lang
        return payload.user_id, normalized_native, normalized_target

    workspace = get_workspace_by_lang_pair(db, normalized_native, normalized_target)
    if workspace is None:
        try:
            workspace = create_workspace(
                db,
                native_lang=normalized_native,
                target_lang=normalized_target,
                goal=payload.goal,
                make_active=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        workspace.goal = payload.goal
        set_active_workspace(db, workspace)

    return workspace.learner_user_id, workspace.native_lang, workspace.target_lang


@router.post("/setup", response_model=ProfileSetupResponse)
def profile_setup(payload: ProfileSetupRequest, db: Session = Depends(get_db)) -> ProfileSetupResponse:
    resolved_user_id, resolved_native, resolved_target = _resolve_user_for_profile_setup(payload, db)
    _get_or_create_user(db, resolved_user_id)

    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == resolved_user_id))
    if profile is None:
        profile = LearnerProfile(
            user_id=resolved_user_id,
            native_lang=resolved_native,
            target_lang=resolved_target,
            level=payload.level,
            goal=payload.goal,
            preferences=payload.preferences,
        )
        db.add(profile)
    else:
        profile.native_lang = resolved_native
        profile.target_lang = resolved_target
        profile.level = payload.level
        profile.goal = payload.goal
        profile.preferences = payload.preferences

    db.commit()
    db.refresh(profile)
    return ProfileSetupResponse(
        user_id=profile.user_id,
        native_lang=profile.native_lang,
        target_lang=profile.target_lang,
        level=profile.level,
        goal=profile.goal,
        preferences=profile.preferences,
    )


@router.get("", response_model=ProfileGetResponse)
def profile_get(user_id: int, db: Session = Depends(get_db)) -> ProfileGetResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileGetResponse(
        user_id=profile.user_id,
        native_lang=profile.native_lang,
        target_lang=profile.target_lang,
        level=profile.level,
        goal=profile.goal,
        preferences=profile.preferences,
    )


@router.post("/placement-test/start", response_model=PlacementStartResponse)
def placement_start(
    payload: PlacementStartRequest, db: Session = Depends(get_db)
) -> PlacementStartResponse:
    try:
        normalized_native = normalize_lang(payload.native_lang)
        normalized_target = normalize_lang(payload.target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if normalized_native == normalized_target:
        raise HTTPException(status_code=400, detail="Native and target language must be different")
    resolved_user_id = payload.user_id
    resolved_native = normalized_native
    resolved_target = normalized_target
    if payload.user_id == LOCAL_OWNER_USER_ID:
        try:
            workspace = create_workspace(
                db,
                native_lang=normalized_native,
                target_lang=normalized_target,
                goal=None,
                make_active=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        resolved_user_id = workspace.learner_user_id
        resolved_native = workspace.native_lang
        resolved_target = workspace.target_lang
    else:
        workspace = get_workspace_for_user(db, payload.user_id)
        if workspace is not None:
            if workspace.native_lang != normalized_native or workspace.target_lang != normalized_target:
                raise HTTPException(
                    status_code=400,
                    detail="Workspace language pair mismatch for this user_id",
                )
            set_active_workspace(db, workspace)
            resolved_native = workspace.native_lang
            resolved_target = workspace.target_lang

    _get_or_create_user(db, resolved_user_id)
    questions = build_placement_questions(resolved_target)

    session = PlacementSession(
        user_id=resolved_user_id,
        native_lang=resolved_native,
        target_lang=resolved_target,
        status="in_progress",
        current_question_index=0,
        questions=questions,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return PlacementStartResponse(
        session_id=session.id,
        question_index=0,
        question=questions[0],
        total_questions=len(questions),
    )


@router.post("/placement-test/answer", response_model=PlacementAnswerResponse)
def placement_answer(
    payload: PlacementAnswerRequest, db: Session = Depends(get_db)
) -> PlacementAnswerResponse:
    session = db.get(PlacementSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Placement session not found")
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="Placement session already finished")

    idx = session.current_question_index
    questions = session.questions
    if idx >= len(questions):
        raise HTTPException(status_code=409, detail="No remaining questions")

    answer_row = PlacementAnswer(
        session_id=session.id,
        question_index=idx,
        prompt=questions[idx],
        answer_text=payload.answer,
        score=score_answer(payload.answer),
    )
    db.add(answer_row)

    next_idx = idx + 1
    done = next_idx >= len(questions)
    session.current_question_index = next_idx
    if done:
        session.status = "ready_to_finish"

    db.commit()
    return PlacementAnswerResponse(
        session_id=session.id,
        accepted_question_index=idx,
        done=done,
        next_question_index=None if done else next_idx,
        next_question=None if done else questions[next_idx],
    )


@router.post("/placement-test/finish", response_model=PlacementFinishResponse)
def placement_finish(
    payload: PlacementFinishRequest, db: Session = Depends(get_db)
) -> PlacementFinishResponse:
    session = db.get(PlacementSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Placement session not found")

    answers = db.scalars(select(PlacementAnswer).where(PlacementAnswer.session_id == session.id)).all()
    if not answers:
        raise HTTPException(status_code=400, detail="No answers submitted")

    avg_score = round(sum(a.score for a in answers) / len(answers), 3)
    level = score_to_cefr(avg_score)
    skill_map = baseline_skill_map(avg_score)

    session.status = "finished"
    session.recommended_level = level
    session.finished_at = utcnow()

    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == session.user_id))
    if profile is None:
        profile = LearnerProfile(
            user_id=session.user_id,
            native_lang=session.native_lang,
            target_lang=session.target_lang,
            level=level,
            preferences={},
        )
        db.add(profile)
    else:
        profile.level = level

    snapshot = SkillSnapshot(user_id=session.user_id, **skill_map)
    db.add(snapshot)

    db.commit()

    return PlacementFinishResponse(
        session_id=session.id,
        level=level,
        avg_score=avg_score,
        skill_map=skill_map,
    )
