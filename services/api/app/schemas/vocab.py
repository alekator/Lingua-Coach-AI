from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VocabAddRequest(BaseModel):
    user_id: int = Field(ge=1)
    word: str = Field(min_length=1, max_length=100)
    translation: str = Field(min_length=1, max_length=255)
    example: str | None = Field(default=None, max_length=2000)
    phonetics: str | None = Field(default=None, max_length=100)


class VocabItemResponse(BaseModel):
    id: int
    user_id: int
    word: str
    translation: str
    example: str | None
    phonetics: str | None
    due_at: datetime | None = None
    interval_days: int | None = None
    ease: float | None = None
    enrichment_source: str | None = None


class VocabListResponse(BaseModel):
    items: list[VocabItemResponse]


class VocabReviewNextRequest(BaseModel):
    user_id: int = Field(ge=1)


class VocabReviewNextResponse(BaseModel):
    has_item: bool
    item: VocabItemResponse | None = None


class VocabReviewSubmitRequest(BaseModel):
    user_id: int = Field(ge=1)
    vocab_item_id: int = Field(ge=1)
    rating: str = Field(pattern="^(again|hard|good|easy)$")


class VocabReviewSubmitResponse(BaseModel):
    vocab_item_id: int
    rating: str
    next_due_at: datetime
    interval_days: int
    ease: float
