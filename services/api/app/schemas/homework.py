from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HomeworkCreateRequest(BaseModel):
    """Request schema for homework create API operations."""
    user_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=255)
    tasks: list[dict] = Field(default_factory=list)
    due_at: datetime | None = None


class HomeworkItem(BaseModel):
    """Schema item representing homework."""
    id: int
    user_id: int
    title: str
    tasks: list[dict]
    status: str
    created_at: datetime
    due_at: datetime | None = None
    submission_count: int = 0
    latest_score: float | None = None
    latest_feedback: str | None = None
    latest_answer_text: str | None = None


class HomeworkListResponse(BaseModel):
    """Response schema for homework list API results."""
    items: list[HomeworkItem]


class HomeworkSubmitRequest(BaseModel):
    """Request schema for homework submit API operations."""
    homework_id: int = Field(ge=1)
    answers: dict = Field(default_factory=dict)


class HomeworkUpdateRequest(BaseModel):
    """Request schema for homework update API operations."""
    title: str = Field(min_length=1, max_length=255)
    tasks: list[dict] = Field(default_factory=list)
    due_at: datetime | None = None
    status: str = Field(min_length=1, max_length=32)


class HomeworkSubmitResponse(BaseModel):
    """Response schema for homework submit API results."""
    homework_id: int
    status: str
    grade: dict
