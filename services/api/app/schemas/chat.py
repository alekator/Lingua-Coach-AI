from __future__ import annotations

from pydantic import BaseModel, Field


class Correction(BaseModel):
    type: str
    bad: str
    good: str
    explanation: str | None = None


class NewWord(BaseModel):
    word: str
    translation: str
    example: str | None = None
    phonetics: str | None = None


class ChatRubricDimension(BaseModel):
    score: int = Field(ge=1, le=5)
    feedback: str


class ChatRubric(BaseModel):
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
    user_id: int = Field(ge=1)
    mode: str = Field(default="chat", min_length=2, max_length=32)


class ChatStartResponse(BaseModel):
    session_id: int
    mode: str
    status: str


class ChatMessageRequest(BaseModel):
    session_id: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    assistant_text: str
    corrections: list[Correction] = Field(default_factory=list)
    new_words: list[NewWord] = Field(default_factory=list)
    homework_suggestions: list[str] = Field(default_factory=list)
    rubric: ChatRubric | None = None
    engine_used: str | None = None


class ChatEndRequest(BaseModel):
    session_id: int = Field(ge=1)


class ChatEndResponse(BaseModel):
    session_id: int
    status: str
