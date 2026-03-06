from __future__ import annotations

import re


TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def text_units(text: str) -> int:
    clean = text.strip()
    if not clean:
        return 0
    tokens = TOKEN_RE.findall(clean)
    cjk_chars = CJK_RE.findall(clean)
    # For CJK-like scripts, token regex can collapse full sentence into one token.
    if cjk_chars and len(tokens) <= 1:
        return len(cjk_chars)
    if tokens:
        return len(tokens)
    # Fallback for scripts where whitespace tokenization is weak.
    if cjk_chars:
        return len(cjk_chars)
    # Generic fallback: count non-space symbols in coarse chunks.
    compact = re.sub(r"\s+", "", clean)
    return max(1, round(len(compact) / 4))


def lexical_diversity(text: str) -> float:
    clean = text.strip()
    if not clean:
        return 0.0
    tokens = [t.lower() for t in TOKEN_RE.findall(clean)]
    cjk_chars = [c for c in CJK_RE.findall(clean)]
    if cjk_chars and len(tokens) <= 1:
        return len(set(cjk_chars)) / max(1, len(cjk_chars))
    if tokens:
        return len(set(tokens)) / max(1, len(tokens))
    if cjk_chars:
        return len(set(cjk_chars)) / max(1, len(cjk_chars))
    compact = re.sub(r"\s+", "", clean).lower()
    if not compact:
        return 0.0
    return len(set(compact)) / max(1, len(compact))
