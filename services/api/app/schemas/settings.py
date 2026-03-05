from __future__ import annotations

from pydantic import BaseModel, Field


class OpenAIKeySetRequest(BaseModel):
    api_key: str = Field(min_length=10, max_length=512)


class OpenAIKeyStatusResponse(BaseModel):
    configured: bool
    source: str
    masked: str | None = None
