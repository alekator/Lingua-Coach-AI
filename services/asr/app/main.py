from __future__ import annotations

import io
import os

from fastapi import FastAPI, File, Form, UploadFile
from openai import OpenAI
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str
    status: str


class AsrTranscribeResponse(BaseModel):
    transcript: str
    language: str = Field(default="unknown")


def default_transcribe(file: UploadFile, language_hint: str) -> AsrTranscribeResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
        audio_bytes = file.file.read()
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(file.filename or "audio.webm", io.BytesIO(audio_bytes), file.content_type or "audio/webm"),
            language=None if language_hint == "auto" else language_hint,
        )
        text = getattr(transcript, "text", "").strip()
        return AsrTranscribeResponse(transcript=text, language=language_hint if language_hint != "auto" else "unknown")

    return AsrTranscribeResponse(
        transcript=f"stub transcript from {file.filename or 'audio'}",
        language=language_hint if language_hint != "auto" else "unknown",
    )


def create_app() -> FastAPI:
    app = FastAPI(title="LinguaCoach ASR", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="asr", status="ok")

    @app.post("/asr/transcribe", response_model=AsrTranscribeResponse)
    def asr_transcribe(
        file: UploadFile = File(...),
        language_hint: str = Form(default="auto"),
    ) -> AsrTranscribeResponse:
        return default_transcribe(file, language_hint)

    return app


app = create_app()
