from __future__ import annotations

from pydantic import BaseModel, Field


class Correction(BaseModel):
    """Data model for correction."""
    type: str
    bad: str
    good: str
    explanation: str | None = None


class NewWord(BaseModel):
    """Data model for new word."""
    word: str
    translation: str
    example: str | None = None
    phonetics: str | None = None


class ChatRubricDimension(BaseModel):
    """Data model for chat rubric dimension."""
    score: int = Field(ge=1, le=5)
    feedback: str


class ChatRubric(BaseModel):
    """Data model for chat rubric."""
    overall_score: int = Field(ge=0, le=100)
    level_band: str
    grammar_accuracy: ChatRubricDimension
    lexical_range: ChatRubricDimension
    fluency_coherence: ChatRubricDimension
    task_completion: ChatRubricDimension
    strengths: list[str] = Field(default_factory=list)
    priority_fixes: list[str] = Field(default_factory=list)
    next_drill: str | None = None


class ChatStartRequest(BaseModel):
    """Request schema for chat start API operations."""
    user_id: int = Field(ge=1)
    mode: str = Field(default="chat", min_length=2, max_length=32)


class ChatStartResponse(BaseModel):
    """Response schema for chat start API results."""
    session_id: int
    mode: str
    status: str


class ChatMessageRequest(BaseModel):
    """Request schema for chat message API operations."""
    session_id: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    """Response schema for chat message API results."""
    assistant_text: str
    corrections: list[Correction] = Field(default_factory=list)
    new_words: list[NewWord] = Field(default_factory=list)
    homework_suggestions: list[str] = Field(default_factory=list)
    rubric: ChatRubric | None = None
    engine_used: str | None = None


class ChatEndRequest(BaseModel):
    """Request schema for chat end API operations."""
    session_id: int = Field(ge=1)


class ChatEndResponse(BaseModel):
    """Response schema for chat end API results."""
    session_id: int
    status: str
