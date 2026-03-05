from __future__ import annotations

from datetime import date

from pydantic import BaseModel


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
