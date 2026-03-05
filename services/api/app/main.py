from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from app.db import init_db
from app.routers.chat import router as chat_router
from app.routers.profile import router as profile_router
from app.routers.translate import router as translate_router
from app.services.teacher import TeacherResponder, default_teacher_responder
from app.services.translate import (
    TranslatorFn,
    TtsSynthesizerFn,
    default_translator,
    default_tts_synthesizer,
)


class HealthResponse(BaseModel):
    service: str
    status: str


class OpenAIDebugResponse(BaseModel):
    status: str
    detail: str


def default_openai_probe() -> tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
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
async def app_lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app(
    openai_probe: Callable[[], tuple[str, str]] | None = None,
    teacher_responder: TeacherResponder | None = None,
    translator: TranslatorFn | None = None,
    tts_synthesizer: TtsSynthesizerFn | None = None,
) -> FastAPI:
    app = FastAPI(title="LinguaCoach API", version="0.1.0", lifespan=app_lifespan)
    probe = openai_probe or default_openai_probe
    app.state.teacher_responder = teacher_responder or default_teacher_responder
    app.state.translator = translator or default_translator
    app.state.tts_synthesizer = tts_synthesizer or default_tts_synthesizer

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
    app.include_router(chat_router)
    app.include_router(translate_router)

    return app


app = create_app()
