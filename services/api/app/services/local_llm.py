from __future__ import annotations

import json
from threading import Lock
from typing import Any

from app.config import settings


_LLAMA_INSTANCE: Any | None = None
_LLAMA_MODEL_PATH: str | None = None
_LLAMA_LOCK = Lock()


def is_local_llm_enabled() -> bool:
    return settings.api_llm_provider.strip().lower() == "local"


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
    model_path = settings.local_llm_model_path.strip()
    if not model_path:
        raise RuntimeError("LOCAL_LLM_MODEL_PATH is not configured")

    with _LLAMA_LOCK:
        if _LLAMA_INSTANCE is not None and _LLAMA_MODEL_PATH == model_path:
            return _LLAMA_INSTANCE

        Llama = _import_llama()
        _LLAMA_INSTANCE = Llama(
            model_path=model_path,
            n_ctx=max(512, settings.local_llm_n_ctx),
            n_threads=max(1, settings.local_llm_n_threads),
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
