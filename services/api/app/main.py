from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from collections import deque
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel

from app.db import SessionLocal, init_db
from app.routers.app_state import router as app_state_router
from app.routers.chat import router as chat_router
from app.routers.homework import router as homework_router
from app.routers.learning import router as learning_router
from app.routers.profile import router as profile_router
from app.routers.progress import router as progress_router
from app.routers.translate import router as translate_router
from app.routers.vocab import router as vocab_router
from app.routers.voice import router as voice_router
from app.routers.settings import router as settings_router
from app.routers.workspaces import router as workspaces_router
from app.services.teacher import TeacherResponder, default_teacher_responder
from app.services.local_llm import get_local_llm_diagnostics
from app.services.provider_config import get_llm_provider
from app.services.openai_key_runtime import get_runtime_openai_key, is_configured_openai_key, set_runtime_openai_key
from app.services.secret_store import get_secret
from app.services.translate import (
    TranslatorFn,
    TtsSynthesizerFn,
    default_translator,
    default_tts_synthesizer,
)
from app.services.voice import (
    AsrTranscriberFn,
    VoiceTeacherFn,
    default_asr_transcriber,
    default_voice_teacher,
)


class HealthResponse(BaseModel):
    """Response schema for health API results."""
    service: str
    status: str


class OpenAIDebugResponse(BaseModel):
    """Response schema for open aidebug API results."""
    status: str
    detail: str


logger = logging.getLogger("linguacoach.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def default_openai_probe() -> tuple[str, str]:
    if get_llm_provider() == "local":
        diag = get_local_llm_diagnostics(run_probe=False)
        if diag["status"] == "ok":
            return ("ok", "Local LLM provider is enabled")
        return ("error", str(diag["message"]))

    api_key = get_runtime_openai_key()
    if not api_key:
        return ("not_configured", "OPENAI_API_KEY is not set")

    try:
        client = OpenAI(api_key=api_key)
        models = client.models.list()
        first_model = next(iter(models.data), None)
        model_name = first_model.id if first_model else "unknown"
        return ("ok", f"OpenAI reachable, sample model: {model_name}")
    except Exception as exc:  # pragma: no cover
        return ("error", str(exc))


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    runtime_key = get_runtime_openai_key()
    if runtime_key:
        app.state.openai_api_key = runtime_key
    else:
        with SessionLocal() as db:
            stored = get_secret(db, "openai_api_key")
            if stored is not None and is_configured_openai_key(stored.value):
                set_runtime_openai_key(stored.value)
                app.state.openai_api_key = stored.value
            else:
                app.state.openai_api_key = None
    yield


def create_app(
    openai_probe: Callable[[], tuple[str, str]] | None = None,
    teacher_responder: TeacherResponder | None = None,
    translator: TranslatorFn | None = None,
    tts_synthesizer: TtsSynthesizerFn | None = None,
    asr_transcriber: AsrTranscriberFn | None = None,
    voice_teacher: VoiceTeacherFn | None = None,
    rate_limit_per_minute: int = 120,
) -> FastAPI:
    app = FastAPI(title="LinguaCoach API", version="0.1.0", lifespan=app_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    probe = openai_probe or default_openai_probe
    app.state.teacher_responder = teacher_responder or default_teacher_responder
    app.state.translator = translator or default_translator
    app.state.tts_synthesizer = tts_synthesizer or default_tts_synthesizer
    app.state.asr_transcriber = asr_transcriber or default_asr_transcriber
    app.state.voice_teacher = voice_teacher or default_voice_teacher
    app.state.rate_limit_per_minute = rate_limit_per_minute
    app.state.rate_limit_store: dict[str, deque[float]] = {}

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                }
            )
        )
        return response

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        if path in {"/health", "/_scaffold", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{path}"
        now = time.time()
        window_sec = 60
        bucket = app.state.rate_limit_store.setdefault(key, deque())
        while bucket and bucket[0] <= now - window_sec:
            bucket.popleft()

        limit = app.state.rate_limit_per_minute
        if len(bucket) >= limit:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": f"Limit is {limit} requests per minute for this endpoint",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id, "Retry-After": "60"},
            )
        bucket.append(now)
        return await call_next(request)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "detail": exc.detail,
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.exception("Unhandled error", extra={"request_id": request_id, "error": str(exc)})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "detail": "Internal server error",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="api", status="ok")

    @app.get("/debug/openai", response_model=OpenAIDebugResponse)
    def debug_openai() -> OpenAIDebugResponse:
        status, detail = probe()
        if status == "error":
            raise HTTPException(status_code=502, detail=detail)
        return OpenAIDebugResponse(status=status, detail=detail)

    # Stage 1 scaffold for future routing groups.
    @app.get("/_scaffold", response_model=dict[str, Any])
    def scaffold() -> dict[str, Any]:
        return {
            "planned_routes": [
                "/auth/*",
                "/profile/*",
                "/chat/*",
                "/voice/*",
                "/translate*",
                "/grammar/*",
                "/vocab/*",
                "/exercises/*",
                "/homework/*",
                "/progress/*",
                "/plan/today",
                "/scenarios",
            ]
        }

    app.include_router(profile_router)
    app.include_router(settings_router)
    app.include_router(app_state_router)
    app.include_router(workspaces_router)
    app.include_router(chat_router)
    app.include_router(translate_router)
    app.include_router(voice_router)
    app.include_router(vocab_router)
    app.include_router(homework_router)
    app.include_router(progress_router)
    app.include_router(learning_router)

    return app


app = create_app()
