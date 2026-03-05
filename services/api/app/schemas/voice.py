from __future__ import annotations

from pydantic import BaseModel


class VoiceTranscribeResponse(BaseModel):
    transcript: str
    language: str


class PronunciationRubric(BaseModel):
    fluency: float
    clarity: float
    grammar_accuracy: float
    vocabulary_range: float
    confidence: float
    overall_score: float
    level_band: str
    actionable_tips: list[str]


class VoiceMessageResponse(BaseModel):
    transcript: str
    teacher_text: str
    audio_url: str
    pronunciation_feedback: str
    pronunciation_rubric: PronunciationRubric


class VoiceProgressPoint(BaseModel):
    date: str
    speaking_score: float


class VoiceProgressResponse(BaseModel):
    user_id: int
    trend: str
    points: list[VoiceProgressPoint]
    pronunciation_mistakes_7d: int
    recommendation: str
