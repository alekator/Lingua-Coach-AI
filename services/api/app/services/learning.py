from __future__ import annotations

from app.schemas.learning import ExerciseItem, ScenarioItem


def default_scenarios() -> list[ScenarioItem]:
    return [
        ScenarioItem(id="travel-hotel", title="Hotel Check-in", description="Practice check-in dialog."),
        ScenarioItem(id="job-interview", title="Job Interview", description="Common interview Q&A."),
        ScenarioItem(id="coffee-shop", title="Coffee Shop", description="Ordering and small talk."),
        ScenarioItem(id="airport-customs", title="Airport Customs", description="Travel control questions."),
    ]


def generate_exercises(exercise_type: str, topic: str, count: int) -> list[ExerciseItem]:
    items: list[ExerciseItem] = []
    for index in range(1, count + 1):
        prompt = f"[{exercise_type}] {topic}: item {index}"
        items.append(
            ExerciseItem(
                id=f"ex-{index}",
                type=exercise_type,
                prompt=prompt,
                expected_answer=f"answer-{index}",
            )
        )
    return items


def grade_exercises(answers: dict[str, str], expected: dict[str, str]) -> tuple[float, float, dict[str, bool]]:
    if not expected:
        return 0.0, 0.0, {}
    details: dict[str, bool] = {}
    correct = 0
    for key, value in expected.items():
        ok = answers.get(key, "").strip().lower() == value.strip().lower()
        details[key] = ok
        if ok:
            correct += 1
    max_score = float(len(expected))
    return float(correct), max_score, details
