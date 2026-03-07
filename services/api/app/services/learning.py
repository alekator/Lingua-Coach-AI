from __future__ import annotations

from collections import Counter
import json
import re
from typing import Any

from openai import OpenAI

from app.schemas.learning import CoachSessionStep, ExerciseItem, ScenarioItem, ScenarioScriptStep
from app.config import settings
from app.services.ai_runtime import log_usage, usage_from_response
from app.services.local_llm import complete_json, is_local_llm_enabled
from app.services.openai_key_runtime import get_runtime_openai_key
from app.services.provider_config import get_llm_provider
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
        "work-standup": [
            ScenarioScriptStep(
                id="done",
                coach_prompt="Give one concise update on what you finished yesterday.",
                expected_keywords=["finished", "task", "yesterday"],
                tip="Use one clear sentence with outcome.",
            ),
            ScenarioScriptStep(
                id="today",
                coach_prompt="State your top priority for today and expected result.",
                expected_keywords=["today", "priority", "result"],
                tip="Name exactly one focus item.",
            ),
            ScenarioScriptStep(
                id="blocker",
                coach_prompt="Describe one blocker and ask for specific support.",
                expected_keywords=["blocked", "need", "help"],
                tip="Mention blocker + concrete ask.",
            ),
        ],
        "work-meeting": [
            ScenarioScriptStep(
                id="proposal",
                coach_prompt="Present a short idea for improving team workflow.",
                expected_keywords=["proposal", "improve", "workflow"],
                tip="State idea, benefit, and scope.",
            ),
            ScenarioScriptStep(
                id="clarify",
                coach_prompt="Answer a follow-up question about timeline or ownership.",
                expected_keywords=["timeline", "owner", "next"],
                tip="Be direct and specific.",
            ),
            ScenarioScriptStep(
                id="align",
                coach_prompt="Confirm action items and meeting next steps.",
                expected_keywords=["action", "confirm", "next"],
                tip="Close with who does what by when.",
            ),
        ],
        "work-feedback": [
            ScenarioScriptStep(
                id="receive",
                coach_prompt="Acknowledge manager feedback and summarize what you heard.",
                expected_keywords=["feedback", "understand", "improve"],
                tip="Paraphrase before reacting.",
            ),
            ScenarioScriptStep(
                id="clarify",
                coach_prompt="Ask one clarifying question about expectations.",
                expected_keywords=["example", "expectation", "question"],
                tip="Ask for measurable criteria.",
            ),
            ScenarioScriptStep(
                id="plan",
                coach_prompt="Commit to one concrete improvement action this week.",
                expected_keywords=["plan", "week", "action"],
                tip="Promise one specific behavior change.",
            ),
        ],
        "work-email": [
            ScenarioScriptStep(
                id="subject",
                coach_prompt="Write an opening line for a professional request email.",
                expected_keywords=["request", "regarding", "hello"],
                tip="Keep opening polite and explicit.",
            ),
            ScenarioScriptStep(
                id="details",
                coach_prompt="Add key details and one deadline.",
                expected_keywords=["details", "deadline", "please"],
                tip="Give context in one compact paragraph.",
            ),
            ScenarioScriptStep(
                id="close",
                coach_prompt="Close with confirmation request and thanks.",
                expected_keywords=["confirm", "thank", "regards"],
                tip="Use a professional closing formula.",
            ),
        ],
        "travel-restaurant": [
            ScenarioScriptStep(
                id="table",
                coach_prompt="Ask for a table and mention party size.",
                expected_keywords=["table", "two", "please"],
                tip="Be polite and concise.",
            ),
            ScenarioScriptStep(
                id="order",
                coach_prompt="Order a meal with one dietary preference.",
                expected_keywords=["order", "without", "please"],
                tip="State preference clearly.",
            ),
            ScenarioScriptStep(
                id="bill",
                coach_prompt="Request the bill and confirm payment method.",
                expected_keywords=["bill", "card", "thank"],
                tip="Close politely with gratitude.",
            ),
        ],
        "travel-emergency": [
            ScenarioScriptStep(
                id="issue",
                coach_prompt="Report an urgent issue (lost bag, injury, or theft).",
                expected_keywords=["help", "lost", "urgent"],
                tip="Lead with the urgent fact first.",
            ),
            ScenarioScriptStep(
                id="location",
                coach_prompt="Share your exact location and current condition.",
                expected_keywords=["location", "now", "need"],
                tip="Give concrete location details.",
            ),
            ScenarioScriptStep(
                id="confirm",
                coach_prompt="Confirm what will happen next and expected timing.",
                expected_keywords=["next", "arrive", "minutes"],
                tip="Repeat support steps to avoid confusion.",
            ),
        ],
        "daily-shopping": [
            ScenarioScriptStep(
                id="find",
                coach_prompt="Ask where to find a product in the store.",
                expected_keywords=["where", "find", "aisle"],
                tip="Name item + ask location.",
            ),
            ScenarioScriptStep(
                id="compare",
                coach_prompt="Compare two options by price or quality.",
                expected_keywords=["price", "better", "difference"],
                tip="Use one comparison phrase.",
            ),
            ScenarioScriptStep(
                id="checkout",
                coach_prompt="Confirm final choice and ask about checkout/payment.",
                expected_keywords=["take", "checkout", "card"],
                tip="End with a clear buying decision.",
            ),
        ],
        "daily-phone-call": [
            ScenarioScriptStep(
                id="intro",
                coach_prompt="Start a practical call and explain why you are calling.",
                expected_keywords=["calling", "about", "need"],
                tip="Open with purpose in one line.",
            ),
            ScenarioScriptStep(
                id="details",
                coach_prompt="Share the key details slowly and clearly.",
                expected_keywords=["details", "number", "time"],
                tip="Chunk details into short phrases.",
            ),
            ScenarioScriptStep(
                id="repeat",
                coach_prompt="Confirm details by repeating them back.",
                expected_keywords=["repeat", "correct", "thank"],
                tip="Always do verbal confirmation.",
            ),
        ],
        "daily-directions": [
            ScenarioScriptStep(
                id="ask",
                coach_prompt="Ask for directions to a specific place.",
                expected_keywords=["how", "get", "station"],
                tip="Mention destination first.",
            ),
            ScenarioScriptStep(
                id="confirm",
                coach_prompt="Confirm route with landmarks or transport.",
                expected_keywords=["left", "right", "bus"],
                tip="Repeat 2-3 key route points.",
            ),
            ScenarioScriptStep(
                id="close",
                coach_prompt="Thank the person and restate your next move.",
                expected_keywords=["thank", "go", "now"],
                tip="Close politely and clearly.",
            ),
        ],
        "daily-neighbor": [
            ScenarioScriptStep(
                id="greeting",
                coach_prompt="Start a friendly conversation with a neighbor.",
                expected_keywords=["hello", "live", "building"],
                tip="Use warm but short opener.",
            ),
            ScenarioScriptStep(
                id="topic",
                coach_prompt="Discuss one practical local topic (noise, parking, deliveries).",
                expected_keywords=["today", "building", "problem"],
                tip="Stay respectful and specific.",
            ),
            ScenarioScriptStep(
                id="followup",
                coach_prompt="Agree on one small follow-up action.",
                expected_keywords=["agree", "tomorrow", "thanks"],
                tip="End with a simple shared next step.",
            ),
        ],
        "study-presentation": [
            ScenarioScriptStep(
                id="opening",
                coach_prompt="Open a short presentation with topic and structure.",
                expected_keywords=["today", "topic", "first"],
                tip="Preview your structure early.",
            ),
            ScenarioScriptStep(
                id="main",
                coach_prompt="Explain one key point with an example.",
                expected_keywords=["example", "because", "important"],
                tip="One argument + one example.",
            ),
            ScenarioScriptStep(
                id="closing",
                coach_prompt="Conclude with takeaway and invite one question.",
                expected_keywords=["summary", "question", "thank"],
                tip="Finish with clear takeaway line.",
            ),
        ],
        "study-debate": [
            ScenarioScriptStep(
                id="position",
                coach_prompt="State your position on a topic in one sentence.",
                expected_keywords=["think", "because", "important"],
                tip="Avoid long intro; state claim quickly.",
            ),
            ScenarioScriptStep(
                id="support",
                coach_prompt="Give two supporting reasons with examples.",
                expected_keywords=["first", "second", "example"],
                tip="Use signposting words for clarity.",
            ),
            ScenarioScriptStep(
                id="respond",
                coach_prompt="Respond politely to an opposing viewpoint.",
                expected_keywords=["understand", "however", "agree"],
                tip="Acknowledge then counter respectfully.",
            ),
        ],
        "study-storytelling": [
            ScenarioScriptStep(
                id="setup",
                coach_prompt="Set scene: where/when and who was there.",
                expected_keywords=["when", "where", "with"],
                tip="Establish context before action.",
            ),
            ScenarioScriptStep(
                id="event",
                coach_prompt="Describe the key event and your reaction.",
                expected_keywords=["suddenly", "happened", "felt"],
                tip="Use sequence markers.",
            ),
            ScenarioScriptStep(
                id="ending",
                coach_prompt="Finish story with outcome and lesson.",
                expected_keywords=["finally", "learned", "next"],
                tip="Close with reflection.",
            ),
        ],
        "service-return": [
            ScenarioScriptStep(
                id="issue",
                coach_prompt="Explain product issue and purchase context.",
                expected_keywords=["bought", "problem", "receipt"],
                tip="State issue factually, not emotionally.",
            ),
            ScenarioScriptStep(
                id="request",
                coach_prompt="Request refund or exchange and give your reason.",
                expected_keywords=["refund", "exchange", "prefer"],
                tip="Ask clearly for one outcome.",
            ),
            ScenarioScriptStep(
                id="negotiate",
                coach_prompt="Negotiate if store offers alternative policy.",
                expected_keywords=["policy", "can", "solution"],
                tip="Stay polite while protecting your goal.",
            ),
        ],
        "service-support": [
            ScenarioScriptStep(
                id="problem",
                coach_prompt="Describe a technical issue to support in one clear summary.",
                expected_keywords=["error", "cannot", "account"],
                tip="Summarize issue in one line first.",
            ),
            ScenarioScriptStep(
                id="steps",
                coach_prompt="List what you already tried before contacting support.",
                expected_keywords=["tried", "restart", "again"],
                tip="Show troubleshooting history.",
            ),
            ScenarioScriptStep(
                id="resolution",
                coach_prompt="Confirm resolution steps and expected follow-up.",
                expected_keywords=["ticket", "next", "email"],
                tip="Repeat support instructions back.",
            ),
        ],
        "networking-event": [
            ScenarioScriptStep(
                id="intro",
                coach_prompt="Introduce yourself and your current focus area.",
                expected_keywords=["work", "focus", "currently"],
                tip="Keep intro under 20 seconds.",
            ),
            ScenarioScriptStep(
                id="exchange",
                coach_prompt="Ask about the other person's role and projects.",
                expected_keywords=["role", "project", "interesting"],
                tip="Ask one open question.",
            ),
            ScenarioScriptStep(
                id="followup",
                coach_prompt="Propose a follow-up message or short call.",
                expected_keywords=["connect", "message", "next"],
                tip="Suggest one realistic next step.",
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


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start >= 0 and end > start:
        candidate = raw_text[start : end + 1]
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Model response is not valid JSON")


def _fallback_generate_exercises(exercise_type: str, topic: str, count: int) -> list[ExerciseItem]:
    normalized_topic = topic.strip().lower() or "general"
    topic_prompts: dict[str, list[tuple[str, str]]] = {
        "grammar": [
            ("Fill the blank: Yesterday I ___ to school.", "went"),
            ("Fix the sentence: She go to work every day.", "She goes to work every day."),
            ("Choose correct form: They ___ dinner now.", "are having"),
            ("Rewrite correctly: I has a new phone.", "I have a new phone."),
            ("Fill the blank: If I ___ time, I will call you.", "have"),
        ],
        "vocab": [
            ("Use a better word: The movie was very ___.", "interesting"),
            ("Complete with one word: I need to ___ a decision.", "make"),
            ("Choose a synonym for 'big': ___", "large"),
            ("Complete the phrase: pay ___ attention", "close"),
            ("Fill the blank: We should ___ this problem.", "solve"),
        ],
        "pronunciation": [
            ("Write stress mark: comPUter or COMputer?", "comPUter"),
            ("Pick natural chunking: I-want-to-go-now / I want to go now", "I want to go now"),
            ("Choose clearer sentence for speaking: I'm gonna / I am going to", "I am going to"),
            ("Mark linked form: next day / nexday", "next day"),
            ("Pick smoother phrase: could you / couldya", "could you"),
        ],
        "speaking": [
            ("Write one short sentence introducing yourself for a meeting.", "I am Alex, and I work in product design."),
            ("Write one sentence about your plan for today.", "Today I will finish my report and send it."),
            ("Ask one polite follow-up question in a conversation.", "Could you tell me more about that?"),
            ("Write one sentence describing a recent task you completed.", "I completed the presentation yesterday."),
            ("Write one sentence giving your opinion politely.", "I think this option is more practical."),
        ],
    }
    bank = topic_prompts.get(normalized_topic, [
        ("Write one clear sentence about your current goal.", "I want to improve my English for work."),
        ("Rewrite this with better grammar: I goed there.", "I went there."),
        ("Fill the blank: I am looking ___ a new job.", "for"),
        ("Write a polite question to request clarification.", "Could you clarify that, please?"),
        ("Write one sentence in present perfect.", "I have finished my homework."),
    ])
    items: list[ExerciseItem] = []
    for index in range(1, count + 1):
        prompt, expected_answer = bank[(index - 1) % len(bank)]
        items.append(
            ExerciseItem(
                id=f"ex-{index}",
                type=exercise_type,
                prompt=prompt,
                expected_answer=expected_answer,
            )
        )
    return items


def _normalize_prompt(prompt: str, exercise_type: str, topic: str, idx: int) -> str:
    clean = prompt.strip()
    if not clean:
        return _fallback_generate_exercises(exercise_type, topic, max(1, idx))[idx - 1].prompt
    if clean.startswith("[") and "]" in clean and ":" in clean:
        right = clean.split(":", 1)[1].strip()
        if right:
            return right[0].upper() + right[1:]
    return clean


def _sanitize_generated_items(
    payload: dict[str, Any],
    exercise_type: str,
    topic: str,
    count: int,
) -> list[ExerciseItem]:
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("Generated payload must contain items list")
    items: list[ExerciseItem] = []
    for idx, raw in enumerate(raw_items[:count], start=1):
        if not isinstance(raw, dict):
            continue
        prompt = str(raw.get("prompt") or "").strip()
        expected_answer = str(raw.get("expected_answer") or "").strip()
        if not prompt or not expected_answer:
            continue
        item_type = str(raw.get("type") or exercise_type).strip() or exercise_type
        item_id = str(raw.get("id") or f"ex-{idx}").strip() or f"ex-{idx}"
        items.append(
            ExerciseItem(
                id=item_id,
                type=item_type,
                prompt=_normalize_prompt(prompt, exercise_type, topic, idx),
                expected_answer=expected_answer,
            )
        )
    if len(items) < count:
        raise ValueError("Not enough valid exercises generated")
    return items


def _generate_exercises_with_local(exercise_type: str, topic: str, count: int) -> list[ExerciseItem]:
    system_prompt = (
        "You are a language drills generator. Return strict JSON only:\n"
        '{ "items": [ { "id": "ex-1", "type": "fill_blank", "prompt": "...", "expected_answer": "..." } ] }\n'
        "Rules: exactly requested count, concise prompts, practical language-learning tasks."
    )
    payload = complete_json(
        system_prompt=system_prompt,
        messages=[
            {
                "role": "user",
                "content": json.dumps(
                    {"exercise_type": exercise_type, "topic": topic, "count": count},
                    ensure_ascii=False,
                ),
            }
        ],
        max_output_tokens=settings.openai_chat_max_output_tokens,
        temperature=settings.openai_temperature_chat,
    )
    return _sanitize_generated_items(payload, exercise_type, topic, count)


def _generate_exercises_with_openai(exercise_type: str, topic: str, count: int) -> list[ExerciseItem]:
    api_key = get_runtime_openai_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=settings.openai_chat_model,
        max_output_tokens=settings.openai_chat_max_output_tokens,
        temperature=settings.openai_temperature_chat,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a language drills generator. Return strict JSON only:\n"
                    '{ "items": [ { "id": "ex-1", "type": "fill_blank", "prompt": "...", "expected_answer": "..." } ] }\n'
                    "Rules: exactly requested count, concise prompts, practical language-learning tasks."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"exercise_type": exercise_type, "topic": topic, "count": count},
                    ensure_ascii=False,
                ),
            },
        ],
    )
    log_usage("exercises_generate", settings.openai_chat_model, usage_from_response(response))
    payload = _extract_json_object(response.output_text)
    return _sanitize_generated_items(payload, exercise_type, topic, count)


def generate_exercises(exercise_type: str, topic: str, count: int) -> list[ExerciseItem]:
    safe_count = max(1, min(20, count))
    normalized_type = exercise_type.strip() or "fill_blank"
    normalized_topic = topic.strip() or "general"
    try:
        provider = get_llm_provider()
        local_available = is_local_llm_enabled()
        has_openai_key = bool(get_runtime_openai_key())

        if provider == "local":
            if local_available:
                try:
                    return _generate_exercises_with_local(normalized_type, normalized_topic, safe_count)
                except Exception:
                    pass
            if has_openai_key:
                return _generate_exercises_with_openai(normalized_type, normalized_topic, safe_count)
            return _fallback_generate_exercises(normalized_type, normalized_topic, safe_count)

        if has_openai_key:
            try:
                return _generate_exercises_with_openai(normalized_type, normalized_topic, safe_count)
            except Exception:
                pass
        if local_available:
            return _generate_exercises_with_local(normalized_type, normalized_topic, safe_count)
        return _fallback_generate_exercises(normalized_type, normalized_topic, safe_count)
    except Exception:
        return _fallback_generate_exercises(normalized_type, normalized_topic, safe_count)


def _fallback_grade_exercises(
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


def _sanitize_grade_payload(
    payload: dict[str, Any],
    expected: dict[str, str],
) -> tuple[float, float, dict[str, bool], dict[str, dict[str, float | str | bool]]]:
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("Grade payload must contain items")
    details: dict[str, bool] = {}
    rubric: dict[str, dict[str, float | str | bool]] = {}
    correct = 0
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        item_id = str(raw.get("id") or "").strip()
        if not item_id or item_id not in expected:
            continue
        ok = bool(raw.get("is_correct", False))
        details[item_id] = ok
        if ok:
            correct += 1
        item_score_raw = raw.get("item_score", 1.0 if ok else 0.0)
        try:
            item_score = max(0.0, min(1.0, float(item_score_raw)))
        except Exception:
            item_score = 1.0 if ok else 0.0
        feedback = str(raw.get("feedback") or ("Exact match." if ok else "Answer differs from expected form.")).strip()
        rubric[item_id] = {
            "is_correct": ok,
            "completeness": 1.0 if ok else 0.5,
            "grammar_quality": 1.0 if ok else 0.6,
            "lexical_quality": 1.0 if ok else 0.6,
            "item_score": round(item_score, 3),
            "feedback": feedback,
        }
    if not details:
        raise ValueError("No grade items were parsed")
    max_score = float(len(expected))
    return float(correct), max_score, details, rubric


def _grade_with_local(
    answers: dict[str, str],
    expected: dict[str, str],
) -> tuple[float, float, dict[str, bool], dict[str, dict[str, float | str | bool]]]:
    system_prompt = (
        "You are a strict drill grader. Return strict JSON only:\n"
        '{ "items": [ { "id": "ex-1", "is_correct": true, "item_score": 1.0, "feedback": "..." } ] }\n'
        "Use expected_answer as reference and keep feedback short."
    )
    payload = complete_json(
        system_prompt=system_prompt,
        messages=[
            {
                "role": "user",
                "content": json.dumps({"answers": answers, "expected": expected}, ensure_ascii=False),
            }
        ],
        max_output_tokens=settings.openai_chat_max_output_tokens,
        temperature=settings.openai_temperature_chat,
    )
    return _sanitize_grade_payload(payload, expected)


def _grade_with_openai(
    answers: dict[str, str],
    expected: dict[str, str],
) -> tuple[float, float, dict[str, bool], dict[str, dict[str, float | str | bool]]]:
    api_key = get_runtime_openai_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=settings.openai_chat_model,
        max_output_tokens=settings.openai_chat_max_output_tokens,
        temperature=settings.openai_temperature_chat,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a strict drill grader. Return strict JSON only:\n"
                    '{ "items": [ { "id": "ex-1", "is_correct": true, "item_score": 1.0, "feedback": "..." } ] }\n'
                    "Use expected_answer as reference and keep feedback short."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"answers": answers, "expected": expected}, ensure_ascii=False),
            },
        ],
    )
    log_usage("exercises_grade", settings.openai_chat_model, usage_from_response(response))
    payload = _extract_json_object(response.output_text)
    return _sanitize_grade_payload(payload, expected)


def grade_exercises(
    answers: dict[str, str],
    expected: dict[str, str],
) -> tuple[float, float, dict[str, bool], dict[str, dict[str, float | str | bool]]]:
    if not expected:
        return 0.0, 0.0, {}, {}
    try:
        provider = get_llm_provider()
        local_available = is_local_llm_enabled()
        has_openai_key = bool(get_runtime_openai_key())

        if provider == "local":
            if local_available:
                try:
                    return _grade_with_local(answers, expected)
                except Exception:
                    pass
            if has_openai_key:
                return _grade_with_openai(answers, expected)
            return _fallback_grade_exercises(answers, expected)

        if has_openai_key:
            try:
                return _grade_with_openai(answers, expected)
            except Exception:
                pass
        if local_available:
            return _grade_with_local(answers, expected)
        return _fallback_grade_exercises(answers, expected)
    except Exception:
        return _fallback_grade_exercises(answers, expected)


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
