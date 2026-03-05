from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceBase(BaseModel):
    id: int
    native_lang: str
    target_lang: str
    goal: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkspaceCreateRequest(BaseModel):
    native_lang: str = Field(min_length=2, max_length=32)
    target_lang: str = Field(min_length=2, max_length=32)
    goal: str | None = Field(default=None, max_length=255)
    make_active: bool = True


class WorkspaceSwitchRequest(BaseModel):
    workspace_id: int = Field(ge=1)


class WorkspaceListResponse(BaseModel):
    owner_user_id: int
    active_workspace_id: int | None
    items: list[WorkspaceBase]


class WorkspaceSwitchResponse(BaseModel):
    active_workspace_id: int
    active_user_id: int


class WorkspaceOverviewItem(BaseModel):
    workspace_id: int
    native_lang: str
    target_lang: str
    goal: str | None
    is_active: bool
    has_profile: bool
    streak_days: int
    minutes_practiced: int
    words_learned: int
    last_activity_at: datetime | None


class WorkspaceOverviewResponse(BaseModel):
    owner_user_id: int
    items: list[WorkspaceOverviewItem]
