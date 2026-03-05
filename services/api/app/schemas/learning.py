from __future__ import annotations

from pydantic import BaseModel, Field


class TranslateVoiceResponse(BaseModel):
    transcript: str
    translated_text: str
    audio_url: str


class GrammarAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    target_lang: str = Field(default="en", min_length=2, max_length=32)


class GrammarError(BaseModel):
    category: str
    bad: str
    good: str
    explanation: str


class GrammarAnalyzeResponse(BaseModel):
    corrected_text: str
    errors: list[GrammarError]
    exercises: list[str]


class ExercisesGenerateRequest(BaseModel):
    user_id: int = Field(ge=1)
    exercise_type: str = Field(default="mixed", min_length=2, max_length=32)
    topic: str = Field(default="general", min_length=2, max_length=100)
    count: int = Field(default=5, ge=1, le=20)


class ExerciseItem(BaseModel):
    id: str
    type: str
    prompt: str
    expected_answer: str


class ExercisesGenerateResponse(BaseModel):
    items: list[ExerciseItem]


class ExercisesGradeRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    expected: dict[str, str] = Field(default_factory=dict)


class ExercisesGradeResponse(BaseModel):
    score: float
    max_score: float
    details: dict[str, bool]
    rubric: dict[str, dict[str, float | str | bool]]


class PlanTodayResponse(BaseModel):
    user_id: int
    time_budget_minutes: int
    focus: list[str]
    tasks: list[str]
    adaptation_notes: list[str] = Field(default_factory=list)


class CoachSessionStep(BaseModel):
    id: str
    title: str
    description: str
    route: str
    duration_minutes: int


class CoachSessionTodayResponse(BaseModel):
    user_id: int
    time_budget_minutes: int
    focus: list[str]
    steps: list[CoachSessionStep]


class ScenarioItem(BaseModel):
    id: str
    title: str
    description: str


class ScenariosResponse(BaseModel):
    items: list[ScenarioItem]


class ScenarioSelectRequest(BaseModel):
    user_id: int = Field(ge=1)
    scenario_id: str = Field(min_length=2, max_length=64)


class ScenarioSelectResponse(BaseModel):
    session_id: int
    mode: str


class ScenarioScriptStep(BaseModel):
    id: str
    coach_prompt: str
    expected_keywords: list[str]
    tip: str


class ScenarioScriptResponse(BaseModel):
    scenario_id: str
    title: str
    description: str
    steps: list[ScenarioScriptStep]


class ScenarioTurnRequest(BaseModel):
    user_id: int = Field(ge=1)
    scenario_id: str = Field(min_length=2, max_length=64)
    step_id: str = Field(min_length=2, max_length=64)
    user_text: str = Field(min_length=1, max_length=4000)


class ScenarioTurnResponse(BaseModel):
    scenario_id: str
    step_id: str
    score: float
    max_score: float
    feedback: str
    next_step_id: str | None = None
    next_prompt: str | None = None
    done: bool
    suggested_reply: str | None = None
