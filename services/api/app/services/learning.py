from __future__ import annotations

from collections import Counter
import re

from app.schemas.learning import CoachSessionStep, ExerciseItem, ScenarioItem, ScenarioScriptStep
from app.services.text_metrics import text_units


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
        ScenarioItem(
            id="relocation-rental",
            title="Apartment Rental",
            description="Ask about rent, utilities, contract terms, and move-in details.",
        ),
        ScenarioItem(
            id="relocation-bank",
            title="Bank Account Setup",
            description="Open an account, verify identity, and clarify account conditions.",
        ),
        ScenarioItem(
            id="relocation-clinic",
            title="Clinic Appointment",
            description="Book an appointment, explain symptoms, and confirm next steps.",
        ),
        ScenarioItem(
            id="work-standup",
            title="Team Standup",
            description="Give concise updates: done, in progress, blocked.",
        ),
        ScenarioItem(
            id="work-meeting",
            title="Project Meeting",
            description="Present an idea, ask follow-up questions, and align on actions.",
        ),
        ScenarioItem(
            id="work-feedback",
            title="Manager Feedback",
            description="Discuss performance feedback and agree on improvement actions.",
        ),
        ScenarioItem(
            id="work-email",
            title="Professional Email",
            description="Formulate clear requests, confirmations, and deadlines.",
        ),
        ScenarioItem(
            id="travel-restaurant",
            title="Restaurant Interaction",
            description="Order food, handle preferences, and request the bill politely.",
        ),
        ScenarioItem(
            id="travel-emergency",
            title="Travel Emergency",
            description="Explain an urgent issue and ask for immediate help.",
        ),
        ScenarioItem(
            id="daily-shopping",
            title="Grocery Shopping",
            description="Ask about product options, prices, and substitutions.",
        ),
        ScenarioItem(
            id="daily-phone-call",
            title="Phone Call Practice",
            description="Handle a short practical call and confirm key details.",
        ),
        ScenarioItem(
            id="daily-directions",
            title="Asking Directions",
            description="Ask for directions, confirm route, and repeat landmarks.",
        ),
        ScenarioItem(
            id="daily-neighbor",
            title="Neighbor Conversation",
            description="Start polite small talk and discuss simple practical topics.",
        ),
        ScenarioItem(
            id="study-presentation",
            title="Mini Presentation",
            description="Present a short topic with structure and transitions.",
        ),
        ScenarioItem(
            id="study-debate",
            title="Opinion Debate",
            description="State and defend an opinion with two supporting points.",
        ),
        ScenarioItem(
            id="study-storytelling",
            title="Storytelling",
            description="Tell a short story with clear sequence and details.",
        ),
        ScenarioItem(
            id="service-return",
            title="Product Return",
            description="Explain issue, request refund/exchange, and negotiate options.",
        ),
        ScenarioItem(
            id="service-support",
            title="Customer Support Chat",
            description="Describe a technical problem and confirm resolution steps.",
        ),
        ScenarioItem(
            id="networking-event",
            title="Networking Event",
            description="Introduce yourself, exchange context, and propose follow-up.",
        ),
    ]


def scenario_scripts() -> dict[str, list[ScenarioScriptStep]]:
    return {
        "travel-hotel": [
                ScenarioScriptStep(
                    id="arrival",
                    coach_prompt="You arrive at a hotel desk. Ask to check in with your reservation.",
                    expected_keywords=["check", "reservation", "name"],
                    tip="Use a polite opener and give one concrete detail.",
                ),
                ScenarioScriptStep(
                    id="request",
                    coach_prompt="Request one change: quiet room, higher floor, or late check-out.",
                    expected_keywords=["room", "please", "late"],
                    tip="State request + reason in one sentence.",
                ),
                ScenarioScriptStep(
                    id="confirm",
                    coach_prompt="Confirm the final details and thank the receptionist.",
                    expected_keywords=["confirm", "thank", "nights"],
                    tip="Repeat key details to avoid mistakes.",
                ),
            ],
        "job-interview": [
                ScenarioScriptStep(
                    id="intro",
                    coach_prompt="Introduce yourself in 2-3 sentences for this role.",
                    expected_keywords=["experience", "role", "skills"],
                    tip="Keep structure: who you are -> relevant experience -> value.",
                ),
                ScenarioScriptStep(
                    id="strength",
                    coach_prompt="Describe one strength with a practical example.",
                    expected_keywords=["example", "project", "result"],
                    tip="Use a mini STAR pattern: situation, action, result.",
                ),
                ScenarioScriptStep(
                    id="question",
                    coach_prompt="Ask one thoughtful question to the interviewer.",
                    expected_keywords=["team", "goals", "question"],
                    tip="Ask about goals, team process, or impact expectations.",
                ),
            ],
        "coffee-shop": [
                ScenarioScriptStep(
                    id="order",
                    coach_prompt="Place your drink order with size and one preference.",
                    expected_keywords=["coffee", "size", "please"],
                    tip="Order pattern: drink + size + adjustment.",
                ),
                ScenarioScriptStep(
                    id="clarify",
                    coach_prompt="Clarify payment method and if take-away is possible.",
                    expected_keywords=["pay", "card", "take"],
                    tip="Ask one short question at a time.",
                ),
                ScenarioScriptStep(
                    id="smalltalk",
                    coach_prompt="Add one short friendly small-talk line before leaving.",
                    expected_keywords=["day", "thank", "nice"],
                    tip="Keep it natural and brief.",
                ),
            ],
        "airport-customs": [
                ScenarioScriptStep(
                    id="purpose",
                    coach_prompt="State purpose of trip, destination, and duration.",
                    expected_keywords=["travel", "days", "destination"],
                    tip="Use simple factual statements.",
                ),
                ScenarioScriptStep(
                    id="documents",
                    coach_prompt="Explain where you will stay and show readiness with documents.",
                    expected_keywords=["hotel", "booking", "documents"],
                    tip="Answer directly without extra detail.",
                ),
                ScenarioScriptStep(
                    id="close",
                    coach_prompt="Close conversation politely and confirm next step.",
                    expected_keywords=["thank", "next", "gate"],
                    tip="Be polite and concise.",
                ),
            ],
        "relocation-rental": [
                ScenarioScriptStep(
                    id="search",
                    coach_prompt="Ask about available apartments and monthly rent range.",
                    expected_keywords=["apartment", "rent", "available"],
                    tip="Ask one clear question, then narrow options.",
                ),
                ScenarioScriptStep(
                    id="terms",
                    coach_prompt="Clarify utilities, deposit, and contract length.",
                    expected_keywords=["utilities", "deposit", "contract"],
                    tip="Group financial terms in one sentence.",
                ),
                ScenarioScriptStep(
                    id="close",
                    coach_prompt="Confirm move-in date and request next steps by message.",
                    expected_keywords=["move", "date", "message"],
                    tip="End with a polite confirmation.",
                ),
            ],
        "relocation-bank": [
                ScenarioScriptStep(
                    id="intent",
                    coach_prompt="Explain that you want to open a bank account.",
                    expected_keywords=["open", "account", "bank"],
                    tip="State intent directly.",
                ),
                ScenarioScriptStep(
                    id="verify",
                    coach_prompt="Provide identity details and ask what documents are required.",
                    expected_keywords=["documents", "passport", "required"],
                    tip="Mention one ID and ask one requirement question.",
                ),
                ScenarioScriptStep(
                    id="confirm",
                    coach_prompt="Confirm fees and online banking setup.",
                    expected_keywords=["fees", "online", "setup"],
                    tip="Repeat critical account conditions.",
                ),
            ],
        "relocation-clinic": [
                ScenarioScriptStep(
                    id="book",
                    coach_prompt="Book an appointment and mention your main symptom.",
                    expected_keywords=["appointment", "symptom", "today"],
                    tip="One symptom, one time request.",
                ),
                ScenarioScriptStep(
                    id="details",
                    coach_prompt="Describe symptom duration and severity briefly.",
                    expected_keywords=["days", "pain", "worse"],
                    tip="Use time + intensity language.",
                ),
                ScenarioScriptStep(
                    id="followup",
                    coach_prompt="Ask about tests, prescription, and next visit.",
                    expected_keywords=["tests", "prescription", "next"],
                    tip="Ask for concrete follow-up.",
                ),
            ],
    }


def build_cefr_prompt_variant(base_prompt: str, level: str) -> str:
    level_u = level.upper()
    if level_u in {"A1", "A2"}:
        return f"{base_prompt} Use short simple sentences (5-9 words)."
    if level_u in {"B1", "B2"}:
        return f"{base_prompt} Add one detail and one polite connector."
    return f"{base_prompt} Add precision and natural phrasing with one follow-up nuance."


def script_for_level(steps: list[ScenarioScriptStep], level: str) -> list[ScenarioScriptStep]:
    return [
        ScenarioScriptStep(
            id=step.id,
            coach_prompt=build_cefr_prompt_variant(step.coach_prompt, level),
            expected_keywords=step.expected_keywords,
            tip=step.tip,
        )
        for step in steps
    ]


def evaluate_scenario_turn(
    *,
    expected_keywords: list[str],
    user_text: str,
    target_lang: str | None = None,
) -> tuple[float, float, str]:
    # Unicode-aware tokenization so scenario scoring is not biased to whitespace-based latin text only.
    tokens = set(re.findall(r"\w+", user_text.lower(), flags=re.UNICODE))
    non_en_mode = bool(target_lang and target_lang.lower() != "en")
    if not expected_keywords:
        ratio = min(1.0, len(tokens) / 8.0)
        if ratio < 0.35:
            return 0.35, 1.0, "You are close. Add one clearer complete sentence."
        return ratio, 1.0, "Good response. Continue to next roleplay step."

    matched = sum(1 for kw in expected_keywords if kw.lower() in tokens)
    max_score = float(len(expected_keywords))
    keyword_ratio = float(matched) / max_score
    fullness_ratio = min(1.0, len(tokens) / 10.0)
    ratio = max(keyword_ratio, 0.55 * keyword_ratio + 0.45 * fullness_ratio)
    if non_en_mode and len(tokens) >= 7:
        ratio = max(ratio, 0.6)
    score = round(max_score * min(1.0, ratio), 3)

    if ratio >= 0.8:
        feedback = "Strong response. It sounds natural and complete for this step."
    elif ratio >= 0.5:
        feedback = "Nice attempt. Add one clearer concrete detail to sound more confident."
    else:
        feedback = "You are close. Try a shorter sentence with the key practical details."
    return score, max_score, feedback


def build_suggested_reply(expected_keywords: list[str], target_lang: str | None = None) -> str:
    if target_lang and target_lang.lower() != "en":
        return "Try one short sentence that answers the prompt, then add one practical detail."
    if not expected_keywords:
        return "Try one short, clear sentence with one practical detail."
    lead = expected_keywords[0]
    tail = expected_keywords[1] if len(expected_keywords) > 1 else "details"
    return f"Example: I want to confirm {lead} and {tail}, please."


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
        answer_len = text_units(answer)
        expected_len = max(1, text_units(expected_clean))
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
