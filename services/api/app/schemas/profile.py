from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileSetupRequest(BaseModel):
    """Request schema for profile setup API operations."""
    user_id: int = Field(ge=1)
    native_lang: str = Field(min_length=2, max_length=32)
    target_lang: str = Field(min_length=2, max_length=32)
    level: str = Field(default="A1", min_length=2, max_length=4)
    goal: str | None = Field(default=None, max_length=255)
    preferences: dict = Field(default_factory=dict)


class ProfileSetupResponse(BaseModel):
    """Response schema for profile setup API results."""
    user_id: int
    native_lang: str
    target_lang: str
    level: str
    goal: str | None
    preferences: dict


class ProfileGetResponse(ProfileSetupResponse):
    """Response schema for profile get API results."""
    pass


class PlacementStartRequest(BaseModel):
    """Request schema for placement start API operations."""
    user_id: int = Field(ge=1)
    native_lang: str = Field(min_length=2, max_length=32)
    target_lang: str = Field(min_length=2, max_length=32)


class PlacementStartResponse(BaseModel):
    """Response schema for placement start API results."""
    session_id: int
    question_index: int
    question: str
    total_questions: int


class PlacementAnswerRequest(BaseModel):
    """Request schema for placement answer API operations."""
    session_id: int = Field(ge=1)
    answer: str = Field(default="", max_length=3000)


class PlacementAnswerResponse(BaseModel):
    """Response schema for placement answer API results."""
    session_id: int
    accepted_question_index: int
    done: bool
    next_question_index: int | None = None
    next_question: str | None = None


class PlacementFinishRequest(BaseModel):
    """Request schema for placement finish API operations."""
    session_id: int = Field(ge=1)


class PlacementFinishResponse(BaseModel):
    """Response schema for placement finish API results."""
    session_id: int
    level: str
    avg_score: float
    skill_map: dict[str, float]
