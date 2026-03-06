from __future__ import annotations

from datetime import datetime, date
from typing import Literal

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


SessionStepStatus = Literal["pending", "in_progress", "completed"]


class CoachSessionStepProgressItem(BaseModel):
    step_id: str
    title: str
    status: SessionStepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CoachSessionProgressResponse(BaseModel):
    user_id: int
    session_date: date
    total_steps: int
    completed_steps: int
    completion_percent: int
    items: list[CoachSessionStepProgressItem]


class CoachSessionProgressUpsertRequest(BaseModel):
    user_id: int = Field(ge=1)
    step_id: str = Field(min_length=2, max_length=64)
    status: SessionStepStatus
    time_budget_minutes: int = Field(default=15, ge=5, le=120)


class CoachErrorBankItem(BaseModel):
    category: str
    occurrences: int
    latest_bad: str
    latest_good: str
    latest_explanation: str | None = None
    last_seen_at: datetime
    drill_prompt: str
    suggested_route: str = "/app/exercises"


class CoachErrorBankResponse(BaseModel):
    user_id: int
    items: list[CoachErrorBankItem]


class CoachNextAction(BaseModel):
    id: str
    title: str
    reason: str
    route: str
    priority: int
    quick_mode_minutes: int | None = Field(default=None, ge=5, le=120)


class CoachNextActionsResponse(BaseModel):
    user_id: int
    items: list[CoachNextAction]


class CoachReactivationResponse(BaseModel):
    user_id: int
    eligible: bool
    gap_days: int
    weak_topic: str | None = None
    title: str
    tasks: list[str] = Field(default_factory=list)
    cta_route: str = "/app/session"
    note: str


class CoachDailyChallengeResponse(BaseModel):
    user_id: int
    title: str
    reason: str
    task: str
    route: str
    estimated_minutes: int


class CoachTrajectoryMilestone(BaseModel):
    day: int
    title: str
    target: str


class CoachTrajectoryResponse(BaseModel):
    user_id: int
    horizon_days: int
    current_phase: str
    retake_recommended: bool
    milestones: list[CoachTrajectoryMilestone]


class CoachRoadmapItem(BaseModel):
    id: str
    title: str
    reason: str
    route: str
    priority: int


class CoachRoadmapResponse(BaseModel):
    user_id: int
    goal: str
    items: list[CoachRoadmapItem]


class OutcomePackItem(BaseModel):
    id: str
    title: str
    target_level: str
    readiness: str
    missing_signals: list[str]
    recommended_route: str


class OutcomePacksResponse(BaseModel):
    user_id: int
    items: list[OutcomePackItem]


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
