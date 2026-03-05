from __future__ import annotations

import json
import logging
from collections import OrderedDict
from typing import Any, Hashable


logger = logging.getLogger("linguacoach.ai")


class SmallLRUCache:
    def __init__(self, max_items: int = 512) -> None:
        self.max_items = max(16, max_items)
        self._store: OrderedDict[Hashable, Any] = OrderedDict()

    def get(self, key: Hashable) -> Any | None:
        if key not in self._store:
            return None
        value = self._store.pop(key)
        self._store[key] = value
        return value

    def set(self, key: Hashable, value: Any) -> None:
        if key in self._store:
            self._store.pop(key)
        elif len(self._store) >= self.max_items:
            self._store.popitem(last=False)
        self._store[key] = value


def usage_from_response(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if not usage:
        return {}
    # SDK object shape can vary between versions; normalize defensively.
    prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + output_tokens) or 0)
    cached_tokens = 0
    prompt_details = getattr(usage, "input_tokens_details", None)
    if prompt_details is not None:
        cached_tokens = int(getattr(prompt_details, "cached_tokens", 0) or 0)
    return {
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_tokens": cached_tokens,
    }


def log_usage(scope: str, model: str, usage: dict[str, int]) -> None:
    if not usage:
        return
    logger.info(
        json.dumps(
            {
                "scope": scope,
                "model": model,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "cached_tokens": usage.get("cached_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
        )
    )
