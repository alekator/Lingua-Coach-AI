from __future__ import annotations

from collections import Counter

from app.schemas.learning import CoachSessionStep, ExerciseItem, ScenarioItem


def default_scenarios() -> list[ScenarioItem]:
    return [
        ScenarioItem(
            id="travel-hotel",
            title="Hotel Check-in",
            description="Handle booking details, requests, and polite clarification at reception.",
        ),
        ScenarioItem(
            id="job-interview",
            title="Job Interview",
            description="Practice concise self-introduction, strengths, and follow-up questions.",
        ),
        ScenarioItem(
            id="coffee-shop",
            title="Coffee Shop",
            description="Train everyday ordering, quick decisions, and friendly small talk.",
        ),
        ScenarioItem(
            id="airport-customs",
            title="Airport Customs",
            description="Answer travel-control questions clearly under mild time pressure.",
        ),
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


def grade_exercises(
    answers: dict[str, str],
    expected: dict[str, str],
) -> tuple[float, float, dict[str, bool], dict[str, dict[str, float | str | bool]]]:
    if not expected:
        return 0.0, 0.0, {}, {}
    details: dict[str, bool] = {}
    rubric: dict[str, dict[str, float | str | bool]] = {}
    correct = 0
    for key, value in expected.items():
        answer = answers.get(key, "").strip()
        expected_clean = value.strip()
        ok = answer.lower() == expected_clean.lower()
        details[key] = ok
        if ok:
            correct += 1

        # Lightweight rubric for MVP scoring transparency.
        answer_len = len(answer.split())
        expected_len = max(1, len(expected_clean.split()))
        completeness = min(1.0, answer_len / expected_len)
        grammar_quality = 1.0 if ok else 0.6 if answer else 0.2
        lexical_quality = 1.0 if answer else 0.0
        item_score = round(
            (0.6 * (1.0 if ok else 0.0)) + (0.2 * completeness) + (0.1 * grammar_quality) + (0.1 * lexical_quality),
            3,
        )
        rubric[key] = {
            "is_correct": ok,
            "completeness": round(completeness, 3),
            "grammar_quality": round(grammar_quality, 3),
            "lexical_quality": round(lexical_quality, 3),
            "item_score": item_score,
            "feedback": "Exact match." if ok else "Close meaning is possible, but expected form differs.",
        }
    max_score = float(len(expected))
    return float(correct), max_score, details, rubric


def build_adaptive_plan(
    *,
    goal: str | None,
    time_budget_minutes: int,
    recent_mistake_categories: list[str],
    due_vocab_count: int,
    recent_user_messages_count: int,
    streak_days: int,
    weekly_sessions: int,
    weakest_skill: str | None,
    weakest_skill_score: float | None,
) -> tuple[list[str], list[str], list[str]]:
    ranked_mistakes = Counter(c for c in recent_mistake_categories if c).most_common()
    adaptation_notes: list[str] = []

    focus: list[str] = []
    if goal:
        focus.append(goal)

    for category, _ in ranked_mistakes:
        if category in {"grammar", "verb_form"} and "grammar" not in focus:
            focus.append("grammar")
        elif category == "pronunciation" and "pronunciation" not in focus:
            focus.append("pronunciation")
        elif category == "vocab" and "vocab" not in focus:
            focus.append("vocab")
        if len(focus) >= 3:
            break

    if due_vocab_count > 0 and "vocab" not in focus:
        focus.append("vocab")
    if recent_user_messages_count < 3 and "speaking" not in focus:
        focus.append("speaking")
    if weakest_skill and weakest_skill not in focus and len(focus) < 3:
        focus.append(weakest_skill)
    if weakest_skill and weakest_skill_score is not None and weakest_skill_score < 50:
        adaptation_notes.append(f"Priority skill: {weakest_skill} ({int(weakest_skill_score)}/100).")

    if weekly_sessions < 3 or streak_days < 2:
        adaptation_notes.append("Low recent consistency detected; plan uses shorter high-impact blocks.")
    elif weekly_sessions >= 5 and streak_days >= 4:
        adaptation_notes.append("Strong consistency detected; plan includes one challenge block.")
    else:
        adaptation_notes.append("Balanced consistency detected; plan keeps steady progression.")

    # Keep compact and stable output shape.
    focus = (focus + ["grammar", "speaking", "vocab"])[:3]

    review_ratio = 0.3
    coach_ratio = 0.35
    if weekly_sessions < 3:
        review_ratio = 0.35
        coach_ratio = 0.3
    elif weekly_sessions >= 5 and streak_days >= 4:
        review_ratio = 0.25
        coach_ratio = 0.4

    review_minutes = max(4, min(8, round(time_budget_minutes * review_ratio)))
    coach_minutes = max(4, min(10, round(time_budget_minutes * coach_ratio)))
    scenario_minutes = max(3, time_budget_minutes - review_minutes - coach_minutes)

    first_focus = focus[0]
    review_task = f"{review_minutes} min: quick review ({first_focus})"
    if due_vocab_count > 0:
        review_task = f"{review_minutes} min: SRS vocab review (due cards: {due_vocab_count})"

    coach_task = f"{coach_minutes} min: teacher chat focused on {focus[1]}"
    if ranked_mistakes:
        top_mistake = ranked_mistakes[0][0]
        coach_task = f"{coach_minutes} min: targeted correction drill ({top_mistake})"
    elif weakest_skill:
        coach_task = f"{coach_minutes} min: targeted correction drill ({weakest_skill})"

    scenario_task = f"{scenario_minutes} min: scenario practice ({focus[2]})"
    if weekly_sessions >= 5 and streak_days >= 4:
        scenario_task = f"{scenario_minutes} min: stretch scenario challenge ({focus[2]})"

    return focus, [review_task, coach_task, scenario_task], adaptation_notes


def build_today_session_steps(focus: list[str], time_budget_minutes: int) -> list[CoachSessionStep]:
    warmup_minutes = max(2, round(time_budget_minutes * 0.15))
    chat_minutes = max(4, round(time_budget_minutes * 0.3))
    drill_minutes = max(3, round(time_budget_minutes * 0.25))
    vocab_minutes = max(3, round(time_budget_minutes * 0.15))
    recap_minutes = max(2, time_budget_minutes - warmup_minutes - chat_minutes - drill_minutes - vocab_minutes)

    return [
        CoachSessionStep(
            id="warmup",
            title="Warmup",
            description=f"Quick activation on {focus[0]} with a short grammar or translate prompt.",
            route="/app/grammar",
            duration_minutes=warmup_minutes,
        ),
        CoachSessionStep(
            id="chat",
            title="Coach Chat",
            description=f"Targeted correction loop on {focus[1]}.",
            route="/app/chat",
            duration_minutes=chat_minutes,
        ),
        CoachSessionStep(
            id="drill",
            title="Targeted Drill",
            description=f"Generate and grade compact exercises for {focus[1]}.",
            route="/app/exercises",
            duration_minutes=drill_minutes,
        ),
        CoachSessionStep(
            id="vocab",
            title="Word Review",
            description="Review due cards and add one new useful word from today.",
            route="/app/vocab",
            duration_minutes=vocab_minutes,
        ),
        CoachSessionStep(
            id="recap",
            title="Recap",
            description="Check profile metrics, then set the next small goal.",
            route="/app/profile",
            duration_minutes=recap_minutes,
        ),
    ]
