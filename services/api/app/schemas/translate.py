from __future__ import annotations

from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    """Request schema for translate API operations."""
    user_id: int | None = Field(default=None, ge=1)
    text: str = Field(min_length=1, max_length=4000)
    source_lang: str = Field(default="auto", min_length=2, max_length=32)
    target_lang: str = Field(min_length=2, max_length=32)
    voice: bool = False
    voice_name: str = Field(default="alloy", min_length=2, max_length=32)


class TranslateResponse(BaseModel):
    """Response schema for translate API results."""
    translated_text: str
    source_lang: str
    target_lang: str
    audio_url: str | None = None
    engine_used: str = "fallback"
