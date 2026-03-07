from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from openai import OpenAI
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for health API results."""
    service: str
    status: str


class AsrTranscribeResponse(BaseModel):
    """Response schema for asr transcribe API results."""
    transcript: str
    language: str = Field(default="unknown")


class ProviderSetRequest(BaseModel):
    """Request schema for provider set API operations."""
    provider: str = Field(pattern="^(openai|local)$")


class ProviderStatusResponse(BaseModel):
    """Response schema for provider status API results."""
    provider: str


class AsrDiagnosticsResponse(BaseModel):
    """Response schema for asr diagnostics API results."""
    provider: str
    status: str
    message: str
    model_path: str | None = None
    model_exists: bool = False
    dependency_available: bool = True
    device: str | None = None
    load_ms: float | None = None
    probe_ms: float | None = None


_LOCAL_ASR_MODEL = None
_LOCAL_ASR_MODEL_PATH = None
_LOCAL_ASR_BACKEND = None


def _resolve_asr_provider() -> str:
    raw = os.getenv("ASR_PROVIDER", "openai").strip().lower()
    if raw in {"openai", "local"}:
        return raw
    return "openai"


def _asr_diagnostics(run_probe: bool = False) -> AsrDiagnosticsResponse:
    provider = _resolve_asr_provider()
    model_path = os.getenv("LOCAL_ASR_MODEL_PATH", "").strip() or "openai/whisper-small"
    model_path_obj = Path(model_path)
    model_exists = model_path_obj.exists()
    backend_hint = "faster-whisper" if (model_path_obj / "model.bin").exists() else "transformers-whisper"
    device = os.getenv("LOCAL_ASR_DEVICE", "auto")
    if provider != "local":
        return AsrDiagnosticsResponse(
            provider=provider,
            status="disabled",
            message="ASR provider is OpenAI",
            model_path=model_path,
            model_exists=model_exists,
            dependency_available=True,
            device=device,
            load_ms=None,
            probe_ms=None,
        )

    load_ms = None
    probe_ms = None
    try:
        import time

        started = time.perf_counter()
        _get_local_asr_model()
        load_ms = round((time.perf_counter() - started) * 1000, 2)
    except HTTPException as exc:
        dep_ok = "faster-whisper" not in exc.detail.lower()
        return AsrDiagnosticsResponse(
            provider=provider,
            status="error",
            message=f"{exc.detail} (backend: {backend_hint})",
            model_path=model_path,
            model_exists=model_exists,
            dependency_available=dep_ok,
            device=device,
            load_ms=load_ms,
            probe_ms=probe_ms,
        )
    except Exception as exc:  # pragma: no cover - defensive diagnostics
        return AsrDiagnosticsResponse(
            provider=provider,
            status="error",
            message=f"Local ASR initialization failed: {exc} (backend: {backend_hint})",
            model_path=model_path,
            model_exists=model_exists,
            dependency_available=False,
            device=device,
            load_ms=load_ms,
            probe_ms=probe_ms,
        )

    if run_probe:
        try:
            import time
            from io import BytesIO

            started = time.perf_counter()
            fake = UploadFile(file=BytesIO(b"fake"), filename="probe.wav")
            local_transcribe(fake, language_hint="auto")
            probe_ms = round((time.perf_counter() - started) * 1000, 2)
        except Exception:
            probe_ms = None

    return AsrDiagnosticsResponse(
        provider=provider,
        status="ok",
        message="ready",
        model_path=model_path,
        model_exists=model_exists,
        dependency_available=True,
        device=device,
        load_ms=load_ms,
        probe_ms=probe_ms,
    )


def _get_local_asr_model():
    global _LOCAL_ASR_MODEL, _LOCAL_ASR_MODEL_PATH, _LOCAL_ASR_BACKEND
    model_path = os.getenv("LOCAL_ASR_MODEL_PATH", "").strip() or "openai/whisper-small"
    if _LOCAL_ASR_MODEL is not None and _LOCAL_ASR_MODEL_PATH == model_path:
        return _LOCAL_ASR_MODEL

    model_path_obj = Path(model_path)
    use_faster_whisper = (model_path_obj / "model.bin").exists()

    if use_faster_whisper:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency
            raise HTTPException(
                status_code=503,
                detail="LOCAL ASR requires faster-whisper. Install it to use ASR_PROVIDER=local.",
            ) from exc

        device = os.getenv("LOCAL_ASR_DEVICE", "auto")
        compute_type = os.getenv("LOCAL_ASR_COMPUTE_TYPE", "int8")
        try:
            _LOCAL_ASR_MODEL = WhisperModel(model_path, device=device, compute_type=compute_type)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"LOCAL ASR failed to load faster-whisper model at '{model_path}': {exc}",
            ) from exc
        _LOCAL_ASR_BACKEND = "faster-whisper"
    else:
        try:
            import torch  # type: ignore[import-not-found]
            from transformers import pipeline  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency
            raise HTTPException(
                status_code=503,
                detail="LOCAL ASR requires transformers+torch for HF Whisper folders without model.bin.",
            ) from exc

        device = -1
        dtype = torch.float32
        try:
            _LOCAL_ASR_MODEL = pipeline(
                "automatic-speech-recognition",
                model=model_path,
                device=device,
                torch_dtype=dtype,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"LOCAL ASR failed to load transformers model at '{model_path}': {exc}",
            ) from exc
        _LOCAL_ASR_BACKEND = "transformers-whisper"

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
        if _LOCAL_ASR_BACKEND == "faster-whisper":
            segments, info = model.transcribe(
                tmp.name,
                language=None if language_hint == "auto" else language_hint,
                vad_filter=True,
            )
            transcript_text = " ".join(seg.text.strip() for seg in segments).strip()
            detected_language = getattr(info, "language", None)
        else:
            result = model(tmp.name)
            transcript_text = str(result.get("text", "")).strip() if isinstance(result, dict) else str(result).strip()
            detected_language = None

    if not transcript_text:
        raise HTTPException(status_code=502, detail="Local ASR returned empty transcript")

    return AsrTranscribeResponse(
        transcript=transcript_text,
        language=(detected_language or language_hint) if language_hint != "auto" else (detected_language or "unknown"),
    )


def default_transcribe(file: UploadFile, language_hint: str, api_key_override: str | None = None) -> AsrTranscribeResponse:
    if _resolve_asr_provider() == "local":
        return local_transcribe(file, language_hint)

    api_key = (api_key_override or "").strip() or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured for ASR")

    try:
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
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI ASR request failed: {exc}") from exc


def create_app() -> FastAPI:
    app = FastAPI(title="LinguaCoach ASR", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="asr", status="ok")

    @app.get("/asr/provider", response_model=ProviderStatusResponse)
    def asr_provider_status() -> ProviderStatusResponse:
        return ProviderStatusResponse(provider=_resolve_asr_provider())

    @app.post("/asr/provider", response_model=ProviderStatusResponse)
    def asr_provider_set(payload: ProviderSetRequest) -> ProviderStatusResponse:
        os.environ["ASR_PROVIDER"] = payload.provider
        return ProviderStatusResponse(provider=_resolve_asr_provider())

    @app.get("/asr/diagnostics", response_model=AsrDiagnosticsResponse)
    def asr_diagnostics(probe: bool = False) -> AsrDiagnosticsResponse:
        return _asr_diagnostics(run_probe=probe)

    @app.post("/asr/transcribe", response_model=AsrTranscribeResponse)
    def asr_transcribe(
        request: Request,
        file: UploadFile = File(...),
        language_hint: str = Form(default="auto"),
    ) -> AsrTranscribeResponse:
        key_override = request.headers.get("X-OpenAI-API-Key")
        return default_transcribe(file, language_hint, api_key_override=key_override)

    return app


app = create_app()
