from __future__ import annotations

from datetime import datetime, date
from typing import Literal

from pydantic import BaseModel, Field


class TranslateVoiceResponse(BaseModel):
    """Response schema for translate voice API results."""
    transcript: str
    translated_text: str
    audio_url: str
    engine_used: str = "fallback"


class GrammarAnalyzeRequest(BaseModel):
    """Request schema for grammar analyze API operations."""
    user_id: int = Field(default=1, ge=1)
    text: str = Field(min_length=1, max_length=5000)
    target_lang: str = Field(default="en", min_length=2, max_length=32)


class GrammarError(BaseModel):
    """Data model for grammar error."""
    category: str
    bad: str
    good: str
    explanation: str


class GrammarAnalyzeResponse(BaseModel):
    """Response schema for grammar analyze API results."""
    corrected_text: str
    errors: list[GrammarError]
    exercises: list[str]


class GrammarHistoryItem(BaseModel):
    """Schema item representing grammar history."""
    id: int
    target_lang: str
    input_text: str
    corrected_text: str
    errors: list[GrammarError]
    exercises: list[str]
    created_at: datetime


class GrammarHistoryResponse(BaseModel):
    """Response schema for grammar history API results."""
    items: list[GrammarHistoryItem]


class ExercisesGenerateRequest(BaseModel):
    """Request schema for exercises generate API operations."""
    user_id: int = Field(ge=1)
    exercise_type: str = Field(default="mixed", min_length=2, max_length=32)
    topic: str = Field(default="general", min_length=2, max_length=100)
    count: int = Field(default=5, ge=1, le=20)


class ExerciseItem(BaseModel):
    """Schema item representing exercise."""
    id: str
    type: str
    prompt: str
    expected_answer: str


class ExercisesGenerateResponse(BaseModel):
    """Response schema for exercises generate API results."""
    items: list[ExerciseItem]


class ExercisesGradeRequest(BaseModel):
    """Request schema for exercises grade API operations."""
    answers: dict[str, str] = Field(default_factory=dict)
    expected: dict[str, str] = Field(default_factory=dict)


class ExercisesGradeResponse(BaseModel):
    """Response schema for exercises grade API results."""
    score: float
    max_score: float
    details: dict[str, bool]
    rubric: dict[str, dict[str, float | str | bool]]


class PlanTodayResponse(BaseModel):
    """Response schema for plan today API results."""
    user_id: int
    time_budget_minutes: int
    focus: list[str]
    tasks: list[str]
    adaptation_notes: list[str] = Field(default_factory=list)


class CoachSessionStep(BaseModel):
    """Data model for coach session step."""
    id: str
    title: str
    description: str
    route: str
    duration_minutes: int


class CoachSessionTodayResponse(BaseModel):
    """Response schema for coach session today API results."""
    user_id: int
    time_budget_minutes: int
    focus: list[str]
    steps: list[CoachSessionStep]


SessionStepStatus = Literal["pending", "in_progress", "completed"]


class CoachSessionStepProgressItem(BaseModel):
    """Schema item representing coach session step progress."""
    step_id: str
    title: str
    status: SessionStepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CoachSessionProgressResponse(BaseModel):
    """Response schema for coach session progress API results."""
    user_id: int
    session_date: date
    total_steps: int
    completed_steps: int
    completion_percent: int
    items: list[CoachSessionStepProgressItem]


class CoachSessionProgressUpsertRequest(BaseModel):
    """Request schema for coach session progress upsert API operations."""
    user_id: int = Field(ge=1)
    step_id: str = Field(min_length=2, max_length=64)
    status: SessionStepStatus
    time_budget_minutes: int = Field(default=15, ge=5, le=120)


class CoachErrorBankItem(BaseModel):
    """Schema item representing coach error bank."""
    category: str
    occurrences: int
    latest_bad: str
    latest_good: str
    latest_explanation: str | None = None
    last_seen_at: datetime
    drill_prompt: str
    suggested_route: str = "/app/exercises"


class CoachErrorBankResponse(BaseModel):
    """Response schema for coach error bank API results."""
    user_id: int
    items: list[CoachErrorBankItem]


class CoachNextAction(BaseModel):
    """Data model for coach next action."""
    id: str
    title: str
    reason: str
    route: str
    priority: int
    quick_mode_minutes: int | None = Field(default=None, ge=5, le=120)


class CoachNextActionsResponse(BaseModel):
    """Response schema for coach next actions API results."""
    user_id: int
    items: list[CoachNextAction]


class CoachReviewQueueItem(BaseModel):
    """Schema item representing coach review queue."""
    id: str
    type: str
    title: str
    reason: str
    route: str
    estimated_minutes: int = Field(ge=2, le=30)
    priority: int = Field(ge=1, le=10)
    due_now: bool = True


class CoachReviewQueueResponse(BaseModel):
    """Response schema for coach review queue API results."""
    user_id: int
    items: list[CoachReviewQueueItem]


class CoachReactivationResponse(BaseModel):
    """Response schema for coach reactivation API results."""
    user_id: int
    eligible: bool
    gap_days: int
    available_minutes: int = 15
    recommended_minutes: int = 5
    plan_mode: str = "micro"
    weak_topic: str | None = None
    title: str
    tasks: list[str] = Field(default_factory=list)
    cta_route: str = "/app/session"
    note: str


class CoachDailyChallengeResponse(BaseModel):
    """Response schema for coach daily challenge API results."""
    user_id: int
    title: str
    reason: str
    task: str
    route: str
    estimated_minutes: int


class CoachTrajectoryMilestone(BaseModel):
    """Data model for coach trajectory milestone."""
    day: int
    title: str
    target: str


class CoachTrajectoryResponse(BaseModel):
    """Response schema for coach trajectory API results."""
    user_id: int
    horizon_days: int
    current_phase: str
    retake_recommended: bool
    milestones: list[CoachTrajectoryMilestone]


class CoachRoadmapItem(BaseModel):
    """Schema item representing coach roadmap."""
    id: str
    title: str
    reason: str
    route: str
    priority: int


class CoachRoadmapResponse(BaseModel):
    """Response schema for coach roadmap API results."""
    user_id: int
    goal: str
    items: list[CoachRoadmapItem]


class OutcomePackItem(BaseModel):
    """Schema item representing outcome pack."""
    id: str
    title: str
    target_level: str
    readiness: str
    missing_signals: list[str]
    recommended_route: str


class OutcomePacksResponse(BaseModel):
    """Response schema for outcome packs API results."""
    user_id: int
    items: list[OutcomePackItem]


class ScenarioItem(BaseModel):
    """Schema item representing scenario."""
    id: str
    title: str
    description: str
    required_level: str = "A1"
    unlocked: bool = True
    gate_reason: str | None = None


class ScenariosResponse(BaseModel):
    """Response schema for scenarios API results."""
    items: list[ScenarioItem]


class ScenarioSelectRequest(BaseModel):
    """Request schema for scenario select API operations."""
    user_id: int = Field(ge=1)
    scenario_id: str = Field(min_length=2, max_length=64)


class ScenarioSelectResponse(BaseModel):
    """Response schema for scenario select API results."""
    session_id: int
    mode: str


class ScenarioScriptStep(BaseModel):
    """Data model for scenario script step."""
    id: str
    coach_prompt: str
    expected_keywords: list[str]
    tip: str


class ScenarioScriptResponse(BaseModel):
    """Response schema for scenario script API results."""
    scenario_id: str
    title: str
    description: str
    steps: list[ScenarioScriptStep]


class ScenarioTurnRequest(BaseModel):
    """Request schema for scenario turn API operations."""
    user_id: int = Field(ge=1)
    scenario_id: str = Field(min_length=2, max_length=64)
    step_id: str = Field(min_length=2, max_length=64)
    user_text: str = Field(min_length=1, max_length=4000)


class ScenarioTurnResponse(BaseModel):
    """Response schema for scenario turn API results."""
    scenario_id: str
    step_id: str
    score: float
    max_score: float
    feedback: str
    next_step_id: str | None = None
    next_prompt: str | None = None
    done: bool
    suggested_reply: str | None = None


class CoachScenarioTrackStepItem(BaseModel):
    """Schema item representing coach scenario track step."""
    order: int
    scenario_id: str
    title: str
    status: str


class CoachScenarioTrackMilestone(BaseModel):
    """Data model for coach scenario track milestone."""
    id: str
    title: str
    required_completed: int
    is_reached: bool


class CoachScenarioTrackItem(BaseModel):
    """Schema item representing coach scenario track."""
    track_id: str
    goal: str
    title: str
    total_steps: int
    completed_steps: int
    completion_percent: int
    next_scenario_id: str | None = None
    steps: list[CoachScenarioTrackStepItem]
    milestones: list[CoachScenarioTrackMilestone]


class CoachScenarioTracksResponse(BaseModel):
    """Response schema for coach scenario tracks API results."""
    user_id: int
    items: list[CoachScenarioTrackItem]
