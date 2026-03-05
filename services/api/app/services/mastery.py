from __future__ import annotations

from app.models import SkillSnapshot
from app.schemas.chat import Correction

SKILL_KEYS = ("speaking", "listening", "grammar", "vocab", "reading", "writing")


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def next_skill_snapshot_from_chat(
    previous: SkillSnapshot | None,
    corrections: list[Correction],
    rubric_overall_score: int | None,
) -> dict[str, float]:
    if previous is None:
        state = {
            "speaking": 45.0,
            "listening": 45.0,
            "grammar": 45.0,
            "vocab": 45.0,
            "reading": 45.0,
            "writing": 45.0,
        }
    else:
        state = {key: float(getattr(previous, key)) for key in SKILL_KEYS}

    if rubric_overall_score is not None:
        # Smooth signal: around 60 is neutral, above/below slightly shifts all skills.
        global_delta = (float(rubric_overall_score) - 60.0) / 20.0
        for key in SKILL_KEYS:
            state[key] += global_delta

    penalties_by_type: dict[str, float] = {
        "grammar": 1.2,
        "vocab": 1.0,
        "fluency": 0.8,
        "style": 0.6,
        "pronunciation": 0.8,
    }
    for correction in corrections:
        ctype = (correction.type or "").lower()
        penalty = penalties_by_type.get(ctype, 0.5)
        if ctype in {"grammar"}:
            state["grammar"] -= penalty
            state["writing"] -= penalty * 0.7
        elif ctype in {"vocab"}:
            state["vocab"] -= penalty
            state["speaking"] -= penalty * 0.4
        elif ctype in {"fluency", "pronunciation"}:
            state["speaking"] -= penalty
            state["listening"] -= penalty * 0.3
        elif ctype in {"style"}:
            state["writing"] -= penalty
        else:
            state["writing"] -= penalty * 0.4

    # Gentle learning reinforcement: completed turn still gives tiny growth in receptive skills.
    state["listening"] += 0.2
    state["reading"] += 0.2

    return {key: _clamp(value) for key, value in state.items()}
