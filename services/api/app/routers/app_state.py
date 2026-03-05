from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LearnerProfile, User
from app.schemas.app_bootstrap import AppBootstrapResponse

router = APIRouter(prefix="/app", tags=["app"])

LOCAL_USER_ID = 1


@router.get("/bootstrap", response_model=AppBootstrapResponse)
def app_bootstrap(db: Session = Depends(get_db)) -> AppBootstrapResponse:
    user = db.get(User, LOCAL_USER_ID)
    if user is None:
        user = User(id=LOCAL_USER_ID)
        db.add(user)
        db.commit()

    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == LOCAL_USER_ID))
    has_profile = profile is not None
    needs_onboarding = not has_profile
    next_step = "onboarding" if needs_onboarding else "dashboard"

    return AppBootstrapResponse(
        user_id=LOCAL_USER_ID,
        has_profile=has_profile,
        needs_onboarding=needs_onboarding,
        next_step=next_step,
    )
