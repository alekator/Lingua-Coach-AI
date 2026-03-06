from __future__ import annotations

import io
import os
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from openai import OpenAI
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str
    status: str


class AsrTranscribeResponse(BaseModel):
    transcript: str
    language: str = Field(default="unknown")


_LOCAL_ASR_MODEL = None
_LOCAL_ASR_MODEL_PATH = None


def _resolve_asr_provider() -> str:
    raw = os.getenv("ASR_PROVIDER", "openai").strip().lower()
    if raw in {"openai", "local"}:
        return raw
    return "openai"


def _get_local_asr_model():
    global _LOCAL_ASR_MODEL, _LOCAL_ASR_MODEL_PATH
    model_path = os.getenv("LOCAL_ASR_MODEL_PATH", "").strip() or "openai/whisper-small"
    if _LOCAL_ASR_MODEL is not None and _LOCAL_ASR_MODEL_PATH == model_path:
        return _LOCAL_ASR_MODEL

    try:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - optional dependency
        raise HTTPException(
            status_code=503,
            detail="LOCAL ASR requires faster-whisper. Install it to use ASR_PROVIDER=local.",
        ) from exc

    device = os.getenv("LOCAL_ASR_DEVICE", "auto")
    compute_type = os.getenv("LOCAL_ASR_COMPUTE_TYPE", "int8")
    _LOCAL_ASR_MODEL = WhisperModel(model_path, device=device, compute_type=compute_type)
    _LOCAL_ASR_MODEL_PATH = model_path
    return _LOCAL_ASR_MODEL


def local_transcribe(file: UploadFile, language_hint: str) -> AsrTranscribeResponse:
    audio_bytes = file.file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio is empty")

    model = _get_local_asr_model()
    suffix = ".webm"
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1]

    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        segments, info = model.transcribe(
            tmp.name,
            language=None if language_hint == "auto" else language_hint,
            vad_filter=True,
        )
        transcript_text = " ".join(seg.text.strip() for seg in segments).strip()

    if not transcript_text:
        raise HTTPException(status_code=502, detail="Local ASR returned empty transcript")

    detected_language = getattr(info, "language", None)
    return AsrTranscribeResponse(
        transcript=transcript_text,
        language=(detected_language or language_hint) if language_hint != "auto" else (detected_language or "unknown"),
    )


def default_transcribe(file: UploadFile, language_hint: str) -> AsrTranscribeResponse:
    if _resolve_asr_provider() == "local":
        return local_transcribe(file, language_hint)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured for ASR")

    client = OpenAI(api_key=api_key)
    audio_bytes = file.file.read()
    transcript = client.audio.transcriptions.create(
        model=os.getenv("OPENAI_ASR_MODEL", "whisper-1"),
        file=(file.filename or "audio.webm", io.BytesIO(audio_bytes), file.content_type or "audio/webm"),
        language=None if language_hint == "auto" else language_hint,
    )
    text = getattr(transcript, "text", "").strip()
    if not text:
        raise HTTPException(status_code=502, detail="ASR provider returned empty transcript")
    detected_language = getattr(transcript, "language", None)
    return AsrTranscribeResponse(
        transcript=text,
        language=(detected_language or language_hint) if language_hint != "auto" else (detected_language or "unknown"),
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
