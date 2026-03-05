from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LearningWorkspace
from app.schemas.workspaces import (
    WorkspaceBase,
    WorkspaceCreateRequest,
    WorkspaceListResponse,
    WorkspaceSwitchRequest,
    WorkspaceSwitchResponse,
)
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
    workspace = create_workspace(
        db,
        native_lang=payload.native_lang,
        target_lang=payload.target_lang,
        goal=payload.goal,
        make_active=payload.make_active,
    )
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
