from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LearnerProfile
from app.schemas.app_bootstrap import AppBootstrapResponse
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
    )
