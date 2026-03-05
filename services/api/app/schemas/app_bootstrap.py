from __future__ import annotations

from pydantic import BaseModel


class AppBootstrapResponse(BaseModel):
    user_id: int
    has_profile: bool
    needs_onboarding: bool
    next_step: str
    owner_user_id: int
    active_workspace_id: int | None = None
    active_workspace_native_lang: str | None = None
    active_workspace_target_lang: str | None = None
    active_workspace_goal: str | None = None
