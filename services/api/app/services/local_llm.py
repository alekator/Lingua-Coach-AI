from __future__ import annotations

import json
import os
import time
from threading import Lock
from typing import Any

from app.config import settings
from app.services.provider_config import get_llm_provider


_LLAMA_INSTANCE: Any | None = None
_LLAMA_MODEL_PATH: str | None = None
_LLAMA_LOCK = Lock()


def is_local_llm_enabled() -> bool:
    return get_llm_provider() == "local"


def _import_llama() -> Any:
    try:
        from llama_cpp import Llama  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "Local LLM requires llama-cpp-python. Install it first "
            "(example: pip install llama-cpp-python)."
        ) from exc
    return Llama


def _get_llama() -> Any:
    global _LLAMA_INSTANCE, _LLAMA_MODEL_PATH
    model_path = os.getenv("LOCAL_LLM_MODEL_PATH", settings.local_llm_model_path).strip()
    if not model_path:
        raise RuntimeError("LOCAL_LLM_MODEL_PATH is not configured")

    with _LLAMA_LOCK:
        if _LLAMA_INSTANCE is not None and _LLAMA_MODEL_PATH == model_path:
            return _LLAMA_INSTANCE

        Llama = _import_llama()
        _LLAMA_INSTANCE = Llama(
            model_path=model_path,
            n_ctx=max(512, int(os.getenv("LOCAL_LLM_N_CTX", settings.local_llm_n_ctx))),
            n_threads=max(1, int(os.getenv("LOCAL_LLM_N_THREADS", settings.local_llm_n_threads))),
            verbose=False,
        )
        _LLAMA_MODEL_PATH = model_path
        return _LLAMA_INSTANCE


def _build_prompt(system_prompt: str, messages: list[dict[str, str]]) -> str:
    chunks = [f"System:\n{system_prompt.strip()}"]
    for msg in messages:
        role = msg.get("role", "user").strip().lower()
        content = msg.get("content", "").strip()
        if not content:
            continue
        if role == "system":
            chunks.append(f"System:\n{content}")
        elif role == "assistant":
            chunks.append(f"Assistant:\n{content}")
        else:
            chunks.append(f"User:\n{content}")
    chunks.append("Assistant:\n")
    return "\n\n".join(chunks)


def _complete(
    system_prompt: str,
    messages: list[dict[str, str]],
    max_output_tokens: int,
    temperature: float,
) -> str:
    llama = _get_llama()
    prompt = _build_prompt(system_prompt, messages)
    result = llama.create_completion(
        prompt=prompt,
        max_tokens=max(32, max_output_tokens),
        temperature=max(0.0, temperature),
        top_p=0.95,
        stop=["\nUser:", "\nSystem:"],
    )
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Local LLM returned empty completion")
    text = str(choices[0].get("text", "")).strip()
    if not text:
        raise RuntimeError("Local LLM returned empty text")
    return text


def complete_text(
    system_prompt: str,
    messages: list[dict[str, str]],
    max_output_tokens: int,
    temperature: float,
) -> str:
    return _complete(system_prompt, messages, max_output_tokens=max_output_tokens, temperature=temperature)


def complete_json(
    system_prompt: str,
    messages: list[dict[str, str]],
    max_output_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    text = _complete(system_prompt, messages, max_output_tokens=max_output_tokens, temperature=temperature)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Local LLM response is not valid JSON")


def get_local_llm_diagnostics(run_probe: bool = False) -> dict[str, Any]:
    model_path = os.getenv("LOCAL_LLM_MODEL_PATH", settings.local_llm_model_path).strip()
    provider = get_llm_provider()
    n_ctx = int(os.getenv("LOCAL_LLM_N_CTX", settings.local_llm_n_ctx))
    n_threads = int(os.getenv("LOCAL_LLM_N_THREADS", settings.local_llm_n_threads))

    status = "ok"
    message = "ready"
    dependency = True
    model_exists = bool(model_path)
    load_ms: float | None = None
    probe_ms: float | None = None

    if provider != "local":
        return {
            "provider": provider,
            "status": "disabled",
            "message": "LLM provider is OpenAI",
            "model_path": model_path or None,
            "model_exists": model_exists,
            "dependency_available": True,
            "device": "cpu",
            "n_ctx": n_ctx,
            "n_threads": n_threads,
            "load_ms": None,
            "probe_ms": None,
        }

    if model_path and "://" not in model_path and not os.path.exists(model_path):
        status = "error"
        message = f"Model path not found: {model_path}"
        model_exists = False

    try:
        start = time.perf_counter()
        _get_llama()
        load_ms = round((time.perf_counter() - start) * 1000, 2)
    except Exception as exc:
        status = "error"
        message = str(exc)
        dependency = "llama-cpp-python" not in str(exc).lower()
        if "llama-cpp-python" in str(exc).lower():
            dependency = False

    if status == "ok" and run_probe:
        try:
            start = time.perf_counter()
            complete_text(
                system_prompt="Answer in one short line.",
                messages=[{"role": "user", "content": "ping"}],
                max_output_tokens=16,
                temperature=0.0,
            )
            probe_ms = round((time.perf_counter() - start) * 1000, 2)
        except Exception as exc:
            status = "error"
            message = f"Probe failed: {exc}"

    return {
        "provider": provider,
        "status": status,
        "message": message,
        "model_path": model_path or None,
        "model_exists": model_exists,
        "dependency_available": dependency,
        "device": "cpu",
        "n_ctx": n_ctx,
        "n_threads": n_threads,
        "load_ms": load_ms,
        "probe_ms": probe_ms,
    }
