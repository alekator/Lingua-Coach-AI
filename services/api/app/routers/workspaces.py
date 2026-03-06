from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    ChatSession,
    Homework,
    HomeworkSubmission,
    LearnerProfile,
    LearningWorkspace,
    Message,
    Mistake,
    PlacementAnswer,
    PlacementSession,
    SkillSnapshot,
    SrsState,
    User,
    VocabItem,
)
from app.schemas.workspaces import (
    WorkspaceBase,
    WorkspaceCreateRequest,
    WorkspaceDeleteResponse,
    WorkspaceListResponse,
    WorkspaceOverviewItem,
    WorkspaceOverviewResponse,
    WorkspaceSwitchRequest,
    WorkspaceSwitchResponse,
    WorkspaceUpdateRequest,
)
from app.services.progress import compute_streak_days
from app.services.workspaces import (
    LOCAL_OWNER_USER_ID,
    create_workspace,
    get_active_workspace,
    get_or_create_local_owner,
    set_active_workspace,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _workspace_to_schema(workspace: LearningWorkspace) -> WorkspaceBase:
    return WorkspaceBase(
        id=workspace.id,
        native_lang=workspace.native_lang,
        target_lang=workspace.target_lang,
        goal=workspace.goal,
        is_active=workspace.is_active,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


@router.get("", response_model=WorkspaceListResponse)
def workspaces_list(db: Session = Depends(get_db)) -> WorkspaceListResponse:
    owner = get_or_create_local_owner(db)
    items = db.scalars(
        select(LearningWorkspace)
        .where(LearningWorkspace.owner_user_id == owner.id)
        .order_by(LearningWorkspace.updated_at.desc(), LearningWorkspace.id.desc())
    ).all()
    active = next((item for item in items if item.is_active), None)
    db.commit()
    return WorkspaceListResponse(
        owner_user_id=owner.id,
        active_workspace_id=active.id if active else None,
        items=[_workspace_to_schema(item) for item in items],
    )


@router.post("", response_model=WorkspaceBase)
def workspace_create(payload: WorkspaceCreateRequest, db: Session = Depends(get_db)) -> WorkspaceBase:
    try:
        workspace = create_workspace(
            db,
            native_lang=payload.native_lang,
            target_lang=payload.target_lang,
            goal=payload.goal,
            make_active=payload.make_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(workspace)
    return _workspace_to_schema(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceBase)
def workspace_update(
    workspace_id: int, payload: WorkspaceUpdateRequest, db: Session = Depends(get_db)
) -> WorkspaceBase:
    owner = get_or_create_local_owner(db)
    workspace = db.scalar(
        select(LearningWorkspace).where(
            LearningWorkspace.id == workspace_id,
            LearningWorkspace.owner_user_id == owner.id,
        )
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace.goal = payload.goal
    db.commit()
    db.refresh(workspace)
    return _workspace_to_schema(workspace)


@router.post("/switch", response_model=WorkspaceSwitchResponse)
def workspace_switch(payload: WorkspaceSwitchRequest, db: Session = Depends(get_db)) -> WorkspaceSwitchResponse:
    owner = get_or_create_local_owner(db)
    workspace = db.scalar(
        select(LearningWorkspace).where(
            LearningWorkspace.id == payload.workspace_id,
            LearningWorkspace.owner_user_id == owner.id,
        )
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    set_active_workspace(db, workspace)
    db.commit()

    return WorkspaceSwitchResponse(
        active_workspace_id=workspace.id,
        active_user_id=workspace.learner_user_id,
    )


@router.get("/active", response_model=WorkspaceSwitchResponse)
def workspace_active(db: Session = Depends(get_db)) -> WorkspaceSwitchResponse:
    owner = get_or_create_local_owner(db)
    workspace = get_active_workspace(db, owner.id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Active workspace not set")
    db.commit()
    return WorkspaceSwitchResponse(
        active_workspace_id=workspace.id,
        active_user_id=workspace.learner_user_id,
    )


@router.get("/overview", response_model=WorkspaceOverviewResponse)
def workspace_overview(db: Session = Depends(get_db)) -> WorkspaceOverviewResponse:
    owner = get_or_create_local_owner(db)
    workspaces = db.scalars(
        select(LearningWorkspace)
        .where(LearningWorkspace.owner_user_id == owner.id)
        .order_by(LearningWorkspace.updated_at.desc(), LearningWorkspace.id.desc())
    ).all()

    items: list[WorkspaceOverviewItem] = []
    for workspace in workspaces:
        user_id = workspace.learner_user_id
        has_profile = (
            db.scalar(select(func.count(LearnerProfile.id)).where(LearnerProfile.user_id == user_id)) or 0
        ) > 0
        sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
        active_dates = []
        for session in sessions:
            if not session.started_at:
                continue
            started = session.started_at
            if started.tzinfo is None:
                active_dates.append(started.date())
            else:
                active_dates.append(started.astimezone(UTC).date())
        streak_days = compute_streak_days(active_dates)
        minutes_practiced = len(sessions) * 8
        words_learned = int(
            db.scalar(select(func.count(VocabItem.id)).where(VocabItem.user_id == user_id)) or 0
        )
        last_activity_at = max(
            (session.started_at for session in sessions if session.started_at is not None),
            default=None,
        )
        items.append(
            WorkspaceOverviewItem(
                workspace_id=workspace.id,
                native_lang=workspace.native_lang,
                target_lang=workspace.target_lang,
                goal=workspace.goal,
                is_active=workspace.is_active,
                has_profile=has_profile,
                streak_days=streak_days,
                minutes_practiced=minutes_practiced,
                words_learned=words_learned,
                last_activity_at=last_activity_at,
            )
        )
    db.commit()
    return WorkspaceOverviewResponse(owner_user_id=owner.id, items=items)


@router.delete("/{workspace_id}", response_model=WorkspaceDeleteResponse)
def workspace_delete(workspace_id: int, db: Session = Depends(get_db)) -> WorkspaceDeleteResponse:
    owner = get_or_create_local_owner(db)
    workspace = db.scalar(
        select(LearningWorkspace).where(
            LearningWorkspace.id == workspace_id,
            LearningWorkspace.owner_user_id == owner.id,
        )
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    fallback = db.scalar(
        select(LearningWorkspace)
        .where(
            LearningWorkspace.owner_user_id == owner.id,
            LearningWorkspace.id != workspace.id,
        )
        .order_by(LearningWorkspace.updated_at.desc(), LearningWorkspace.id.desc())
    )
    if fallback is None:
        raise HTTPException(status_code=400, detail="Cannot delete the last workspace")
    learner_user_id = workspace.learner_user_id

    placement_session_ids = db.scalars(
        select(PlacementSession.id).where(PlacementSession.user_id == learner_user_id)
    ).all()
    if placement_session_ids:
        db.query(PlacementAnswer).filter(PlacementAnswer.session_id.in_(placement_session_ids)).delete(
            synchronize_session=False
        )
    db.query(PlacementSession).filter(PlacementSession.user_id == learner_user_id).delete(
        synchronize_session=False
    )

    chat_session_ids = db.scalars(select(ChatSession.id).where(ChatSession.user_id == learner_user_id)).all()
    if chat_session_ids:
        db.query(Message).filter(Message.session_id.in_(chat_session_ids)).delete(synchronize_session=False)
    db.query(ChatSession).filter(ChatSession.user_id == learner_user_id).delete(synchronize_session=False)

    homework_ids = db.scalars(select(Homework.id).where(Homework.user_id == learner_user_id)).all()
    if homework_ids:
        db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id.in_(homework_ids)).delete(
            synchronize_session=False
        )
    db.query(Homework).filter(Homework.user_id == learner_user_id).delete(synchronize_session=False)

    vocab_ids = db.scalars(select(VocabItem.id).where(VocabItem.user_id == learner_user_id)).all()
    if vocab_ids:
        db.query(SrsState).filter(SrsState.vocab_item_id.in_(vocab_ids)).delete(synchronize_session=False)
    db.query(VocabItem).filter(VocabItem.user_id == learner_user_id).delete(synchronize_session=False)

    db.query(LearnerProfile).filter(LearnerProfile.user_id == learner_user_id).delete(synchronize_session=False)
    db.query(SkillSnapshot).filter(SkillSnapshot.user_id == learner_user_id).delete(synchronize_session=False)
    db.query(Mistake).filter(Mistake.user_id == learner_user_id).delete(synchronize_session=False)

    db.delete(workspace)
    db.query(User).filter(User.id == learner_user_id).delete(synchronize_session=False)

    set_active_workspace(db, fallback)

    db.commit()
    return WorkspaceDeleteResponse(
        deleted_workspace_id=workspace_id,
        active_workspace_id=fallback.id,
    )
