from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ProgressSummaryResponse(BaseModel):
    streak_days: int
    minutes_practiced: int
    words_learned: int
    speaking: float
    listening: float
    grammar: float
    vocab: float
    reading: float
    writing: float


class ProgressSkillMapResponse(BaseModel):
    speaking: float
    listening: float
    grammar: float
    vocab: float
    reading: float
    writing: float


class ProgressStreakResponse(BaseModel):
    streak_days: int
    active_dates: list[date]


class ProgressJournalEntry(BaseModel):
    session_id: int
    started_at: date
    mode: str
    messages_count: int
    completed: bool


class ProgressJournalResponse(BaseModel):
    weekly_minutes: int
    weekly_sessions: int
    weak_areas: list[str]
    next_actions: list[str]
    entries: list[ProgressJournalEntry]


class WeeklyGoalSetRequest(BaseModel):
    user_id: int = Field(ge=1)
    target_minutes: int = Field(ge=30, le=2000)


class WeeklyGoalResponse(BaseModel):
    user_id: int
    target_minutes: int
    completed_minutes: int
    remaining_minutes: int
    completion_percent: int
    is_completed: bool


class RewardItem(BaseModel):
    id: str
    title: str
    description: str
    requirement: str
    xp_points: int
    status: str


class ProgressRewardsResponse(BaseModel):
    user_id: int
    total_xp: int
    claimed_count: int
    items: list[RewardItem]


class RewardClaimRequest(BaseModel):
    user_id: int = Field(ge=1)
    reward_id: str = Field(min_length=3, max_length=64)


class ProgressWeeklyReviewResponse(BaseModel):
    user_id: int
    weekly_minutes: int
    weekly_sessions: int
    weekly_goal_target_minutes: int
    weekly_goal_completed: bool
    streak_days: int
    strongest_skill: str
    weakest_skill: str
    top_weak_area: str | None = None
    wins: list[str]
    next_focus: str


class ProgressOutcomesResponse(BaseModel):
    user_id: int
    current_level: str
    estimated_level_from_skills: str
    avg_skill_score: float
    improvement_7d_points: float
    weekly_sessions: int
    streak_days: int
    confidence: str
    recommendations: list[str]
