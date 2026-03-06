from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.schemas.settings import (
    AIRuntimeSetRequest,
    AIRuntimeStatusResponse,
    LanguageCapabilitiesResponse,
    AIModuleDiagnostics,
    OpenAIKeySetRequest,
    OpenAIKeyStatusResponse,
    UsageBudgetSetRequest,
    UsageBudgetStatusResponse,
)
from app.services.local_llm import get_local_llm_diagnostics
from app.services.language_capabilities import get_pair_capabilities
from app.services.openai_key_runtime import get_runtime_openai_key, is_configured_openai_key, set_runtime_openai_key
from app.services.provider_config import get_asr_provider, get_llm_provider, get_tts_provider, set_runtime_providers
from app.services.secret_store import get_secret, set_secret
from app.services.usage_budget import get_usage_budget_snapshot, upsert_usage_budget_settings

router = APIRouter(prefix="/settings", tags=["settings"])


def _mask_key(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _restore_runtime_providers(db: Session) -> None:
    llm = get_secret(db, "ai_provider_llm")
    asr = get_secret(db, "ai_provider_asr")
    tts = get_secret(db, "ai_provider_tts")
    set_runtime_providers(
        llm.value if llm is not None else get_llm_provider(),
        asr.value if asr is not None else get_asr_provider(),
        tts.value if tts is not None else get_tts_provider(),
    )


def _fetch_remote_diag(url: str, provider: str, fallback_message: str, run_probe: bool) -> AIModuleDiagnostics:
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=6.0) as client:
            response = client.get(url, params={"probe": "true" if run_probe else "false"})
            response.raise_for_status()
            payload = response.json()
        probe_ms = round((time.perf_counter() - started) * 1000, 2)
        return AIModuleDiagnostics(
            provider=provider,
            status=str(payload.get("status", "ok")),
            message=str(payload.get("message", "ready")),
            model_path=payload.get("model_path"),
            model_exists=bool(payload.get("model_exists", False)),
            dependency_available=bool(payload.get("dependency_available", True)),
            device=payload.get("device"),
            load_ms=payload.get("load_ms"),
            probe_ms=payload.get("probe_ms", probe_ms),
        )
    except Exception as exc:
        return AIModuleDiagnostics(
            provider=provider,
            status="error",
            message=f"{fallback_message}: {exc}",
            model_path=None,
            model_exists=False,
            dependency_available=False,
            device=None,
            load_ms=None,
            probe_ms=None,
        )


def _ensure_runtime_openai_key(db: Session) -> tuple[str | None, str]:
    runtime_key = get_runtime_openai_key()
    if runtime_key:
        return runtime_key, "env"
    stored = get_secret(db, "openai_api_key")
    if stored is not None and is_configured_openai_key(stored.value):
        set_runtime_openai_key(stored.value)
        return stored.value, "secure_store"
    return None, "none"


@router.get("/openai-key", response_model=OpenAIKeyStatusResponse)
def openai_key_status(db: Session = Depends(get_db)) -> OpenAIKeyStatusResponse:
    key, source = _ensure_runtime_openai_key(db)
    if key:
        stored = get_secret(db, "openai_api_key")
        db.commit()
        return OpenAIKeyStatusResponse(
            configured=True,
            source=source,
            masked=_mask_key(key),
            persistent=stored is not None,
            secure_storage=(stored.storage == "dpapi") if stored is not None else False,
        )
    set_runtime_openai_key(None)
    db.commit()
    return OpenAIKeyStatusResponse(configured=False, source="none", masked=None, persistent=False, secure_storage=False)


@router.post("/openai-key", response_model=OpenAIKeyStatusResponse)
def openai_key_set(payload: OpenAIKeySetRequest, db: Session = Depends(get_db)) -> OpenAIKeyStatusResponse:
    value = payload.api_key.strip()
    set_runtime_openai_key(value)
    storage = set_secret(db, "openai_api_key", value)
    db.commit()
    return OpenAIKeyStatusResponse(
        configured=True,
        source="secure_store",
        masked=_mask_key(value),
        persistent=True,
        secure_storage=storage == "dpapi",
    )


@router.get("/ai-runtime", response_model=AIRuntimeStatusResponse)
def ai_runtime_status(probe: bool = False, db: Session = Depends(get_db)) -> AIRuntimeStatusResponse:
    _ensure_runtime_openai_key(db)
    _restore_runtime_providers(db)
    db.commit()
    llm_provider = get_llm_provider()
    asr_provider = get_asr_provider()
    tts_provider = get_tts_provider()

    llm_diag_raw = get_local_llm_diagnostics(run_probe=probe)
    llm_diag = AIModuleDiagnostics(**llm_diag_raw)
    asr_diag = _fetch_remote_diag(
        f"{settings.asr_url}/asr/diagnostics",
        provider=asr_provider,
        fallback_message="ASR diagnostics unavailable",
        run_probe=probe,
    )
    tts_diag = _fetch_remote_diag(
        f"{settings.tts_url}/tts/diagnostics",
        provider=tts_provider,
        fallback_message="TTS diagnostics unavailable",
        run_probe=probe,
    )

    return AIRuntimeStatusResponse(
        llm_provider=llm_provider,
        asr_provider=asr_provider,
        tts_provider=tts_provider,
        llm=llm_diag,
        asr=asr_diag,
        tts=tts_diag,
    )


@router.post("/ai-runtime", response_model=AIRuntimeStatusResponse)
def ai_runtime_set(payload: AIRuntimeSetRequest, db: Session = Depends(get_db)) -> AIRuntimeStatusResponse:
    set_runtime_providers(payload.llm_provider, payload.asr_provider, payload.tts_provider)
    set_secret(db, "ai_provider_llm", payload.llm_provider)
    set_secret(db, "ai_provider_asr", payload.asr_provider)
    set_secret(db, "ai_provider_tts", payload.tts_provider)
    db.commit()

    # Best-effort push runtime provider to ASR/TTS services.
    for url, provider in (
        (f"{settings.asr_url}/asr/provider", payload.asr_provider),
        (f"{settings.tts_url}/tts/provider", payload.tts_provider),
    ):
        try:
            with httpx.Client(timeout=4.0) as client:
                client.post(url, json={"provider": provider}).raise_for_status()
        except Exception:
            # Diagnostics endpoint will surface if remote provider switch failed.
            pass

    return ai_runtime_status(probe=False, db=db)


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
