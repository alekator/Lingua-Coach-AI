from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HomeworkCreateRequest(BaseModel):
    user_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=255)
    tasks: list[dict] = Field(default_factory=list)
    due_at: datetime | None = None


class HomeworkItem(BaseModel):
    id: int
    user_id: int
    title: str
    tasks: list[dict]
    status: str
    created_at: datetime
    due_at: datetime | None = None


class HomeworkListResponse(BaseModel):
    items: list[HomeworkItem]


class HomeworkSubmitRequest(BaseModel):
    homework_id: int = Field(ge=1)
    answers: dict = Field(default_factory=dict)


class HomeworkSubmitResponse(BaseModel):
    homework_id: int
    status: str
    grade: dict
