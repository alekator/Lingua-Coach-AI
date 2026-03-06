from __future__ import annotations

import os
_INVALID_KEY_VALUES = {"", "sk-...", "your_openai_api_key", "replace_me"}


def is_configured_openai_key(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip()
    if not normalized:
        return False
    if normalized.lower() in _INVALID_KEY_VALUES:
        return False
    # Common placeholder pattern used in docs/examples.
    if normalized.startswith("sk-") and normalized.endswith("..."):
        return False
    return True


def set_runtime_openai_key(value: str | None) -> None:
    if is_configured_openai_key(value):
        normalized = value.strip()
        os.environ["OPENAI_API_KEY"] = normalized
        return
    os.environ.pop("OPENAI_API_KEY", None)


def get_runtime_openai_key() -> str | None:
    env_key = os.getenv("OPENAI_API_KEY")
    if is_configured_openai_key(env_key):
        return env_key.strip()
    return None
