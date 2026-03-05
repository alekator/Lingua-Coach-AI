from __future__ import annotations

from pydantic import BaseModel, Field


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


class AppResetRequest(BaseModel):
    confirmation: str = Field(min_length=1)


class AppResetResponse(BaseModel):
    status: str
    deleted_users: int
    deleted_workspaces: int
    deleted_profiles: int
    deleted_vocab_items: int
    deleted_chat_sessions: int
    openai_key_cleared: bool
