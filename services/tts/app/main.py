from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str
    status: str


class TtsSpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="en", min_length=2, max_length=32)
    voice: str = Field(default="alloy", min_length=2, max_length=32)


class TtsSpeakResponse(BaseModel):
    audio_url: str
    mime_type: str = "audio/mpeg"


def _audio_dir() -> Path:
    root = Path(os.getenv("TTS_AUDIO_DIR", "./generated_audio")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _synthesize_speech(text: str, voice: str) -> bytes:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured for TTS")
    client = OpenAI(api_key=api_key)
    response = client.audio.speech.create(
        model=os.getenv("OPENAI_TTS_MODEL", "tts-1"),
        voice=voice,
        input=text,
        format="mp3",
    )
    content = response.read()
    if not content:
        raise HTTPException(status_code=502, detail="TTS provider returned empty audio")
    return content


def create_app() -> FastAPI:
    app = FastAPI(title="LinguaCoach TTS", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="tts", status="ok")

    @app.post("/tts/speak", response_model=TtsSpeakResponse)
    def tts_speak(payload: TtsSpeakRequest) -> TtsSpeakResponse:
        digest = hashlib.sha1(f"{payload.voice}:{payload.language}:{payload.text}".encode("utf-8")).hexdigest()[:20]
        file_name = f"{payload.voice}-{digest}.mp3"
        out_path = _audio_dir() / file_name
        if not out_path.exists():
            out_path.write_bytes(_synthesize_speech(payload.text, payload.voice))
        return TtsSpeakResponse(audio_url=f"/audio/{file_name}")

    @app.get("/audio/{file_name}")
    def audio_file(file_name: str) -> FileResponse:
        if "/" in file_name or "\\" in file_name:
            raise HTTPException(status_code=400, detail="Invalid file name")
        out_path = _audio_dir() / file_name
        if not out_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        return FileResponse(out_path, media_type="audio/mpeg")

    return app


app = create_app()
