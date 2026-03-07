from __future__ import annotations

from pydantic import BaseModel


class VoiceTranscribeResponse(BaseModel):
    """Response schema for voice transcribe API results."""
    transcript: str
    language: str


class PronunciationRubric(BaseModel):
    """Data model for pronunciation rubric."""
    fluency: float
    clarity: float
    grammar_accuracy: float
    vocabulary_range: float
    confidence: float
    overall_score: float
    level_band: str
    actionable_tips: list[str]


class VoiceMessageResponse(BaseModel):
    """Response schema for voice message API results."""
    transcript: str
    teacher_text: str
    audio_url: str
    pronunciation_feedback: str
    pronunciation_rubric: PronunciationRubric


class VoiceProgressPoint(BaseModel):
    """Data model for voice progress point."""
    date: str
    speaking_score: float


class VoiceProgressResponse(BaseModel):
    """Response schema for voice progress API results."""
    user_id: int
    trend: str
    points: list[VoiceProgressPoint]
    pronunciation_mistakes_7d: int
    recommendation: str
