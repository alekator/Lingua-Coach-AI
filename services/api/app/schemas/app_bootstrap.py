from __future__ import annotations

from pydantic import BaseModel


class AppBootstrapResponse(BaseModel):
    user_id: int
    has_profile: bool
    needs_onboarding: bool
    next_step: str
