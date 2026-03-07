from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceBase(BaseModel):
    """Base schema shared across workspace payloads."""
    id: int
    native_lang: str
    target_lang: str
    goal: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkspaceCreateRequest(BaseModel):
    """Request schema for workspace create API operations."""
    native_lang: str = Field(min_length=2, max_length=32)
    target_lang: str = Field(min_length=2, max_length=32)
    goal: str | None = Field(default=None, max_length=255)
    make_active: bool = True


class WorkspaceUpdateRequest(BaseModel):
    """Request schema for workspace update API operations."""
    goal: str | None = Field(default=None, max_length=255)


class WorkspaceSwitchRequest(BaseModel):
    """Request schema for workspace switch API operations."""
    workspace_id: int = Field(ge=1)


class WorkspaceListResponse(BaseModel):
    """Response schema for workspace list API results."""
    owner_user_id: int
    active_workspace_id: int | None
    items: list[WorkspaceBase]


class WorkspaceSwitchResponse(BaseModel):
    """Response schema for workspace switch API results."""
    active_workspace_id: int
    active_user_id: int


class WorkspaceOverviewItem(BaseModel):
    """Schema item representing workspace overview."""
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
    """Response schema for workspace overview API results."""
    owner_user_id: int
    items: list[WorkspaceOverviewItem]


class WorkspaceDeleteResponse(BaseModel):
    """Response schema for workspace delete API results."""
    deleted_workspace_id: int
    active_workspace_id: int | None
