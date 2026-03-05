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
