from __future__ import annotations

from app.models import LearnerProfile
from app.services.teacher import build_resilient_teacher_fallback, build_teacher_payload


def test_teacher_payload_policy_constraints_eval() -> None:
    profile = LearnerProfile(
        user_id=1,
        native_lang="ru",
        target_lang="en",
        level="B1",
        goal="job interview",
        preferences={"strictness": "high", "daily_minutes": 40, "persona_style": "examiner"},
    )
    payload = build_teacher_payload(profile=profile, mode="chat", user_text="I has done task", history=[])
    policy = payload["coaching_policy"]
    assert policy["strictness"] == "high"
    assert policy["max_corrections"] == 3
    assert policy["session_intensity"] == "intense"
    assert policy["persona_style"] == "examiner"
    assert policy["must_sound_human"] is True


def test_teacher_fallback_is_not_generic_eval() -> None:
    payload = {
        "user_input": "I did a mistake yesterday",
        "learner_profile": {
            "level": "A2",
            "goal": "travel",
            "weak_topics": ["grammar"],
            "preferences": {"strictness": "medium"},
        },
    }
    fallback = build_resilient_teacher_fallback(payload, reason="eval")
    assert "Goal focus: travel" in fallback.assistant_text
    assert "grammar" in fallback.assistant_text
    assert "Micro-step" in fallback.assistant_text
    assert fallback.rubric is not None
