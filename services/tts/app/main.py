from __future__ import annotations

import hashlib
import json
import os
import wave
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
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


class ProviderSetRequest(BaseModel):
    provider: str = Field(pattern="^(openai|local)$")


class ProviderStatusResponse(BaseModel):
    provider: str


class TtsDiagnosticsResponse(BaseModel):
    provider: str
    status: str
    message: str
    model_path: str | None = None
    model_exists: bool = False
    dependency_available: bool = True
    device: str | None = None
    load_ms: float | None = None
    probe_ms: float | None = None


def _audio_dir() -> Path:
    root = Path(os.getenv("TTS_AUDIO_DIR", "./generated_audio")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_tts_provider() -> str:
    raw = os.getenv("TTS_PROVIDER", "openai").strip().lower()
    if raw in {"openai", "local"}:
        return raw
    return "openai"


def _load_model_type(model_path: str) -> str | None:
    config_path = Path(model_path) / "config.json"
    if not config_path.exists():
        return None
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    model_type = raw.get("model_type")
    return model_type if isinstance(model_type, str) else None


def _is_qwen3_tts_model(model_path: str) -> bool:
    return _load_model_type(model_path) == "qwen3_tts"


def _to_qwen_language_name(language: str) -> str:
    lang_map = {
        "zh": "Chinese",
        "en": "English",
        "ja": "Japanese",
        "ko": "Korean",
        "de": "German",
        "fr": "French",
        "ru": "Russian",
        "pt": "Portuguese",
        "es": "Spanish",
        "it": "Italian",
    }
    code = language.strip().lower().split("-", 1)[0]
    return lang_map.get(code, "English")


def _to_qwen_speaker(voice: str, language: str) -> str:
    supported = {
        "vivian",
        "serena",
        "uncle_fu",
        "dylan",
        "eric",
        "ryan",
        "aiden",
        "ono_anna",
        "sohee",
    }
    normalized = voice.strip().lower()
    if normalized in supported:
        return voice
    base = language.strip().lower().split("-", 1)[0]
    # Qwen3-TTS public speaker set has strongest EN voices for generic multilingual usage.
    if base in {"en", "de", "fr", "ru", "es", "pt", "it"}:
        return "Ryan"
    if base == "ja":
        return "Ono_Anna"
    if base == "ko":
        return "Sohee"
    return "Ryan"


def _tts_diagnostics(run_probe: bool = False) -> TtsDiagnosticsResponse:
    provider = _resolve_tts_provider()
    model_path = os.getenv("LOCAL_TTS_MODEL_PATH", "").strip()
    model_exists = bool(model_path and Path(model_path).exists())
    device = "cpu"

    if provider != "local":
        return TtsDiagnosticsResponse(
            provider=provider,
            status="disabled",
            message="TTS provider is OpenAI",
            model_path=model_path or None,
            model_exists=model_exists,
            dependency_available=True,
            device=device,
            load_ms=None,
            probe_ms=None,
        )

    if not model_path:
        return TtsDiagnosticsResponse(
            provider=provider,
            status="error",
            message="LOCAL_TTS_MODEL_PATH is not configured for local TTS",
            model_path=None,
            model_exists=False,
            dependency_available=True,
            device=device,
            load_ms=None,
            probe_ms=None,
        )

    is_qwen3 = _is_qwen3_tts_model(model_path)
    if is_qwen3:
        try:
            import qwen_tts  # type: ignore[import-not-found]
            import torch  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency
            return TtsDiagnosticsResponse(
                provider=provider,
                status="error",
                message=f"Local TTS dependency issue (qwen-tts): {exc}",
                model_path=model_path,
                model_exists=model_exists,
                dependency_available=False,
                device=device,
                load_ms=None,
                probe_ms=None,
            )
    else:
        try:
            import numpy as np  # type: ignore[import-not-found]
            from transformers import pipeline  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency
            return TtsDiagnosticsResponse(
                provider=provider,
                status="error",
                message=f"Local TTS dependency issue: {exc}",
                model_path=model_path,
                model_exists=model_exists,
                dependency_available=False,
                device=device,
                load_ms=None,
                probe_ms=None,
            )

    load_ms = None
    probe_ms = None
    if run_probe:
        try:
            import time
            if is_qwen3:
                from qwen_tts import Qwen3TTSModel  # type: ignore[import-not-found]

                started = time.perf_counter()
                model = Qwen3TTSModel.from_pretrained(
                    model_path,
                    device_map="cpu",
                    dtype="auto",
                )
                load_ms = round((time.perf_counter() - started) * 1000, 2)
                started = time.perf_counter()
                wavs, _sr = model.generate_custom_voice(
                    text="Hello",
                    language="English",
                    speaker="Ryan",
                    instruct="",
                )
                _ = wavs[0]
                probe_ms = round((time.perf_counter() - started) * 1000, 2)
            else:
                import numpy as np  # type: ignore[import-not-found]
                from transformers import pipeline  # type: ignore[import-not-found]

                started = time.perf_counter()
                text_to_audio = pipeline("text-to-audio", model=model_path, trust_remote_code=True)
                load_ms = round((time.perf_counter() - started) * 1000, 2)
                started = time.perf_counter()
                audio = text_to_audio("hello", forward_params={"language": "en", "speaker": "alloy"})
                _ = np.asarray(audio.get("audio"), dtype=np.float32)
                probe_ms = round((time.perf_counter() - started) * 1000, 2)
        except Exception as exc:
            return TtsDiagnosticsResponse(
                provider=provider,
                status="error",
                message=f"Local TTS probe failed: {exc}",
                model_path=model_path,
                model_exists=model_exists,
                dependency_available=True,
                device=device,
                load_ms=load_ms,
                probe_ms=probe_ms,
            )

    return TtsDiagnosticsResponse(
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


def _synthesize_openai_speech(text: str, voice: str, api_key_override: str | None = None) -> bytes:
    api_key = (api_key_override or "").strip() or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured for TTS")
    try:
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
        try:
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format="mp3",
            )
        except TypeError:
            # Backward compatibility for SDK versions that still use `format`.
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                format="mp3",
            )
        content = response.read()
        if not content:
            raise HTTPException(status_code=502, detail="TTS provider returned empty audio")
        return content
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI TTS request failed: {exc}") from exc


def _synthesize_local_speech(text: str, language: str, voice: str) -> bytes:
    model_path = os.getenv("LOCAL_TTS_MODEL_PATH", "").strip()
    if not model_path:
        raise HTTPException(status_code=503, detail="LOCAL_TTS_MODEL_PATH is not configured for local TTS")

    is_qwen3 = _is_qwen3_tts_model(model_path)
    if is_qwen3:
        try:
            import numpy as np  # type: ignore[import-not-found]
            from qwen_tts import Qwen3TTSModel  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency
            raise HTTPException(
                status_code=503,
                detail="Local Qwen3-TTS requires qwen-tts and numpy. Install local TTS dependencies first.",
            ) from exc

        try:
            model = Qwen3TTSModel.from_pretrained(
                model_path,
                device_map="cpu",
                dtype="auto",
            )
            wavs, sample_rate = model.generate_custom_voice(
                text=text,
                language=_to_qwen_language_name(language),
                speaker=_to_qwen_speaker(voice, language),
                instruct="",
            )
            audio_arr = wavs[0] if wavs else None
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Local TTS generation failed: {exc}") from exc
    else:
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
            audio_arr = result.get("audio")
            sample_rate = int(result.get("sampling_rate", 24000))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Local TTS generation failed: {exc}") from exc

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

    @app.get("/tts/provider", response_model=ProviderStatusResponse)
    def tts_provider_status() -> ProviderStatusResponse:
        return ProviderStatusResponse(provider=_resolve_tts_provider())

    @app.post("/tts/provider", response_model=ProviderStatusResponse)
    def tts_provider_set(payload: ProviderSetRequest) -> ProviderStatusResponse:
        os.environ["TTS_PROVIDER"] = payload.provider
        return ProviderStatusResponse(provider=_resolve_tts_provider())

    @app.get("/tts/diagnostics", response_model=TtsDiagnosticsResponse)
    def tts_diagnostics(probe: bool = False) -> TtsDiagnosticsResponse:
        return _tts_diagnostics(run_probe=probe)

    @app.post("/tts/speak", response_model=TtsSpeakResponse)
    def tts_speak(payload: TtsSpeakRequest, request: Request) -> TtsSpeakResponse:
        provider = _resolve_tts_provider()
        digest = hashlib.sha1(f"{payload.voice}:{payload.language}:{payload.text}".encode("utf-8")).hexdigest()[:20]
        extension = "wav" if provider == "local" else "mp3"
        mime_type = "audio/wav" if provider == "local" else "audio/mpeg"
        file_name = f"{payload.voice}-{digest}.{extension}"
        out_path = _audio_dir() / file_name
        key_override = request.headers.get("X-OpenAI-API-Key")
        if not out_path.exists():
            if provider == "local":
                out_path.write_bytes(_synthesize_local_speech(payload.text, payload.language, payload.voice))
            else:
                out_path.write_bytes(_synthesize_openai_speech(payload.text, payload.voice, api_key_override=key_override))
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
