from __future__ import annotations

import os

from fastapi import APIRouter

from app.schemas.settings import OpenAIKeySetRequest, OpenAIKeyStatusResponse

router = APIRouter(prefix="/settings", tags=["settings"])


def _mask_key(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


@router.get("/openai-key", response_model=OpenAIKeyStatusResponse)
def openai_key_status() -> OpenAIKeyStatusResponse:
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return OpenAIKeyStatusResponse(configured=True, source="env", masked=_mask_key(key))
    return OpenAIKeyStatusResponse(configured=False, source="none", masked=None)


@router.post("/openai-key", response_model=OpenAIKeyStatusResponse)
def openai_key_set(payload: OpenAIKeySetRequest) -> OpenAIKeyStatusResponse:
    value = payload.api_key.strip()
    os.environ["OPENAI_API_KEY"] = value
    return OpenAIKeyStatusResponse(configured=True, source="env", masked=_mask_key(value))
