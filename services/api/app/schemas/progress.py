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
