from __future__ import annotations

from app.schemas.chat import ChatMessageResponse
from app.services.learning import grade_exercises
from app.services.placement import score_answer
from app.services.teacher import build_fallback_rubric
from app.services.voice import build_pronunciation_rubric


def test_score_answer_handles_cjk_without_spaces() -> None:
    short = score_answer("你好")
    medium = score_answer("我今天学习中文也练习口语")
    assert short >= 0.25
    assert medium >= 0.5
    assert medium >= short


def test_teacher_fallback_rubric_handles_cjk_input() -> None:
    response = ChatMessageResponse(
        assistant_text="ok",
        corrections=[],
        new_words=[],
        homework_suggestions=[],
    )
    rubric = build_fallback_rubric("我想用中文练习面试表达", response)
    assert rubric.overall_score >= 35
    assert rubric.fluency_coherence.score >= 2


def test_pronunciation_rubric_handles_cjk_input() -> None:
    rubric = build_pronunciation_rubric("我今天练习发音和句子节奏")
    assert rubric["overall_score"] >= 35
    assert rubric["fluency"] >= 35


def test_grade_exercises_uses_language_agnostic_lengths() -> None:
    score, max_score, details, rubric = grade_exercises(
        answers={"ex-1": "我今天去学校"},
        expected={"ex-1": "我今天去学校"},
    )
    assert score == 1.0
    assert max_score == 1.0
    assert details["ex-1"] is True
    assert rubric["ex-1"]["completeness"] >= 0.5

