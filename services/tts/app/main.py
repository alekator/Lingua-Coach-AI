from __future__ import annotations

import hashlib
import os
import wave
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


def _resolve_tts_provider() -> str:
    raw = os.getenv("TTS_PROVIDER", "openai").strip().lower()
    if raw in {"openai", "local"}:
        return raw
    return "openai"


def _synthesize_openai_speech(text: str, voice: str) -> bytes:
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


def _synthesize_local_speech(text: str, language: str, voice: str) -> bytes:
    model_path = os.getenv("LOCAL_TTS_MODEL_PATH", "").strip()
    if not model_path:
        raise HTTPException(status_code=503, detail="LOCAL_TTS_MODEL_PATH is not configured for local TTS")

    try:
        import numpy as np  # type: ignore[import-not-found]
        from transformers import pipeline  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - optional dependency
        raise HTTPException(
            status_code=503,
            detail="Local TTS requires transformers and numpy. Install local TTS dependencies first.",
        ) from exc

    try:
        text_to_audio = pipeline("text-to-audio", model=model_path, trust_remote_code=True)
        result = text_to_audio(
            text,
            forward_params={
                "language": language,
                "speaker": voice,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Local TTS generation failed: {exc}") from exc

    audio_arr = result.get("audio")
    sample_rate = int(result.get("sampling_rate", 24000))
    if audio_arr is None:
        raise HTTPException(status_code=502, detail="Local TTS returned empty audio")

    audio_np = np.asarray(audio_arr, dtype=np.float32)
    if audio_np.ndim > 1:
        audio_np = audio_np.squeeze()
    audio_np = np.clip(audio_np, -1.0, 1.0)
    pcm = (audio_np * 32767.0).astype(np.int16).tobytes()

    # WAV bytes in-memory (mono, 16-bit PCM)
    from io import BytesIO

    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return buffer.getvalue()


def create_app() -> FastAPI:
    app = FastAPI(title="LinguaCoach TTS", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="tts", status="ok")

    @app.post("/tts/speak", response_model=TtsSpeakResponse)
    def tts_speak(payload: TtsSpeakRequest) -> TtsSpeakResponse:
        provider = _resolve_tts_provider()
        digest = hashlib.sha1(f"{payload.voice}:{payload.language}:{payload.text}".encode("utf-8")).hexdigest()[:20]
        extension = "wav" if provider == "local" else "mp3"
        mime_type = "audio/wav" if provider == "local" else "audio/mpeg"
        file_name = f"{payload.voice}-{digest}.{extension}"
        out_path = _audio_dir() / file_name
        if not out_path.exists():
            if provider == "local":
                out_path.write_bytes(_synthesize_local_speech(payload.text, payload.language, payload.voice))
            else:
                out_path.write_bytes(_synthesize_openai_speech(payload.text, payload.voice))
        return TtsSpeakResponse(audio_url=f"/audio/{file_name}", mime_type=mime_type)

    @app.get("/audio/{file_name}")
    def audio_file(file_name: str) -> FileResponse:
        if "/" in file_name or "\\" in file_name:
            raise HTTPException(status_code=400, detail="Invalid file name")
        out_path = _audio_dir() / file_name
        if not out_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        media_type = "audio/wav" if out_path.suffix.lower() == ".wav" else "audio/mpeg"
        return FileResponse(out_path, media_type=media_type)

    return app


app = create_app()
