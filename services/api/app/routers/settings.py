from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.settings import (
    LanguageCapabilitiesResponse,
    OpenAIKeySetRequest,
    OpenAIKeyStatusResponse,
    UsageBudgetSetRequest,
    UsageBudgetStatusResponse,
)
from app.services.language_capabilities import get_pair_capabilities
from app.services.secret_store import get_secret, set_secret
from app.services.usage_budget import get_usage_budget_snapshot, upsert_usage_budget_settings

router = APIRouter(prefix="/settings", tags=["settings"])


def _mask_key(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


@router.get("/openai-key", response_model=OpenAIKeyStatusResponse)
def openai_key_status(db: Session = Depends(get_db)) -> OpenAIKeyStatusResponse:
    key = os.getenv("OPENAI_API_KEY")
    if key:
        stored = get_secret(db, "openai_api_key")
        db.commit()
        return OpenAIKeyStatusResponse(
            configured=True,
            source="env",
            masked=_mask_key(key),
            persistent=stored is not None,
            secure_storage=(stored.storage == "dpapi") if stored is not None else False,
        )
    stored = get_secret(db, "openai_api_key")
    if stored is not None:
        os.environ["OPENAI_API_KEY"] = stored.value
        db.commit()
        return OpenAIKeyStatusResponse(
            configured=True,
            source="secure_store",
            masked=_mask_key(stored.value),
            persistent=True,
            secure_storage=stored.storage == "dpapi",
        )
    db.commit()
    return OpenAIKeyStatusResponse(configured=False, source="none", masked=None, persistent=False, secure_storage=False)


@router.post("/openai-key", response_model=OpenAIKeyStatusResponse)
def openai_key_set(payload: OpenAIKeySetRequest, db: Session = Depends(get_db)) -> OpenAIKeyStatusResponse:
    value = payload.api_key.strip()
    os.environ["OPENAI_API_KEY"] = value
    storage = set_secret(db, "openai_api_key", value)
    db.commit()
    return OpenAIKeyStatusResponse(
        configured=True,
        source="secure_store",
        masked=_mask_key(value),
        persistent=True,
        secure_storage=storage == "dpapi",
    )


@router.get("/usage-budget", response_model=UsageBudgetStatusResponse)
def usage_budget_status(user_id: int, db: Session = Depends(get_db)) -> UsageBudgetStatusResponse:
    if user_id < 1:
        raise HTTPException(status_code=422, detail="user_id must be >= 1")
    snapshot = get_usage_budget_snapshot(db, user_id)
    return UsageBudgetStatusResponse(user_id=user_id, **snapshot.__dict__)


@router.post("/usage-budget", response_model=UsageBudgetStatusResponse)
def usage_budget_set(payload: UsageBudgetSetRequest, db: Session = Depends(get_db)) -> UsageBudgetStatusResponse:
    try:
        snapshot = upsert_usage_budget_settings(
            db,
            user_id=payload.user_id,
            daily_token_cap=payload.daily_token_cap,
            weekly_token_cap=payload.weekly_token_cap,
            warning_threshold=payload.warning_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return UsageBudgetStatusResponse(user_id=payload.user_id, **snapshot.__dict__)


@router.get("/language-capabilities", response_model=LanguageCapabilitiesResponse)
def language_capabilities(native_lang: str, target_lang: str) -> LanguageCapabilitiesResponse:
    try:
        caps = get_pair_capabilities(native_lang, target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LanguageCapabilitiesResponse(**caps.__dict__)
