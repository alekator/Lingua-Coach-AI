from __future__ import annotations

from datetime import datetime, UTC


def build_placement_questions(target_lang: str) -> list[str]:
    return [
        f"Write a short self-introduction in {target_lang}.",
        f"Translate this into {target_lang}: 'I studied yesterday and will study tomorrow.'",
        f"Answer in {target_lang}: What did you do last weekend?",
        f"Create 2 sentences in {target_lang} using past and future tense.",
        f"In {target_lang}, explain your current language-learning goal in 2-3 sentences.",
    ]


def score_answer(answer: str) -> float:
    text = answer.strip()
    if not text:
        return 0.0
    word_count = len(text.split())
    if word_count <= 3:
        return 0.25
    if word_count <= 8:
        return 0.5
    if word_count <= 20:
        return 0.75
    return 1.0


def score_to_cefr(avg_score: float) -> str:
    if avg_score < 0.2:
        return "A1"
    if avg_score < 0.35:
        return "A2"
    if avg_score < 0.5:
        return "B1"
    if avg_score < 0.7:
        return "B2"
    if avg_score < 0.85:
        return "C1"
    return "C2"


def baseline_skill_map(avg_score: float) -> dict[str, float]:
    base = round(avg_score * 100, 1)
    return {
        "speaking": max(0.0, base - 8),
        "listening": max(0.0, base - 4),
        "grammar": max(0.0, base - 6),
        "vocab": max(0.0, base - 5),
        "reading": max(0.0, base - 2),
        "writing": max(0.0, base - 7),
    }


def utcnow() -> datetime:
    return datetime.now(UTC)
