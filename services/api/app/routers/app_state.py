from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LearnerProfile
from app.schemas.app_bootstrap import AppBootstrapResponse, AppResetRequest, AppResetResponse
from app.services.reset import reset_local_app_data
from app.services.workspaces import LOCAL_OWNER_USER_ID, get_active_workspace, get_or_create_local_owner

router = APIRouter(prefix="/app", tags=["app"])


@router.get("/bootstrap", response_model=AppBootstrapResponse)
def app_bootstrap(db: Session = Depends(get_db)) -> AppBootstrapResponse:
    owner = get_or_create_local_owner(db)
    active_workspace = get_active_workspace(db, owner.id)
    active_user_id = active_workspace.learner_user_id if active_workspace else LOCAL_OWNER_USER_ID
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == active_user_id))
    has_profile = profile is not None
    needs_onboarding = not has_profile
    next_step = "onboarding" if needs_onboarding else "dashboard"
    db.commit()

    return AppBootstrapResponse(
        user_id=active_user_id,
        has_profile=has_profile,
        needs_onboarding=needs_onboarding,
        next_step=next_step,
        owner_user_id=owner.id,
        active_workspace_id=active_workspace.id if active_workspace else None,
        active_workspace_native_lang=active_workspace.native_lang if active_workspace else None,
        active_workspace_target_lang=active_workspace.target_lang if active_workspace else None,
        active_workspace_goal=active_workspace.goal if active_workspace else None,
    )


@router.post("/reset", response_model=AppResetResponse)
def app_reset(payload: AppResetRequest, db: Session = Depends(get_db)) -> AppResetResponse:
    if payload.confirmation.strip().upper() != "RESET":
        raise HTTPException(status_code=400, detail="Confirmation token must be RESET")
    summary = reset_local_app_data(db)
    return AppResetResponse(
        status="ok",
        deleted_users=int(summary["deleted_users"]),
        deleted_workspaces=int(summary["deleted_workspaces"]),
        deleted_profiles=int(summary["deleted_profiles"]),
        deleted_vocab_items=int(summary["deleted_vocab_items"]),
        deleted_chat_sessions=int(summary["deleted_chat_sessions"]),
        openai_key_cleared=bool(summary["openai_key_cleared"]),
    )
