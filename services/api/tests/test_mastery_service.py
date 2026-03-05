from __future__ import annotations

from app.models import SkillSnapshot
from app.schemas.chat import Correction
from app.services.mastery import next_skill_snapshot_from_chat


def test_next_skill_snapshot_from_chat_without_previous() -> None:
    snapshot = next_skill_snapshot_from_chat(previous=None, corrections=[], rubric_overall_score=70)
    assert snapshot["speaking"] >= 45
    assert snapshot["grammar"] >= 45
    assert snapshot["reading"] >= 45


def test_next_skill_snapshot_from_chat_applies_correction_penalties() -> None:
    previous = SkillSnapshot(
        user_id=1,
        speaking=60,
        listening=60,
        grammar=60,
        vocab=60,
        reading=60,
        writing=60,
    )
    snapshot = next_skill_snapshot_from_chat(
        previous=previous,
        corrections=[Correction(type="grammar", bad="I has", good="I have", explanation="aux")],
        rubric_overall_score=60,
    )
    assert snapshot["grammar"] < 60
    assert snapshot["writing"] < 60
