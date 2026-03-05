from __future__ import annotations

from pydantic import BaseModel


class VoiceTranscribeResponse(BaseModel):
    transcript: str
    language: str


class VoiceMessageResponse(BaseModel):
    transcript: str
    teacher_text: str
    audio_url: str
    pronunciation_feedback: str
