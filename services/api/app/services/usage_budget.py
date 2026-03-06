from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AIUsageEvent, LearnerProfile

DEFAULT_DAILY_TOKEN_CAP = 12000
DEFAULT_WEEKLY_TOKEN_CAP = 60000
DEFAULT_WARNING_THRESHOLD = 0.8


@dataclass(frozen=True)
class UsageBudgetSnapshot:
    daily_token_cap: int
    weekly_token_cap: int
    warning_threshold: float
    daily_used_tokens: int
    weekly_used_tokens: int
    daily_remaining_tokens: int
    weekly_remaining_tokens: int
    daily_warning: bool
    weekly_warning: bool
    blocked: bool


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _day_start(now: datetime) -> datetime:
    return datetime(now.year, now.month, now.day, tzinfo=UTC)


def _week_start(now: datetime) -> datetime:
    day_start = _day_start(now)
    return day_start - timedelta(days=day_start.weekday())


def estimate_text_tokens(*texts: str) -> int:
    joined = " ".join(texts).strip()
    if not joined:
        return 0
    return max(1, ceil(len(joined) / 4))


def _extract_budget_preferences(preferences: dict | None) -> tuple[int, int, float]:
    prefs = preferences or {}
    raw = prefs.get("usage_budget", {})
    if not isinstance(raw, dict):
        raw = {}
    daily = raw.get("daily_token_cap", DEFAULT_DAILY_TOKEN_CAP)
    weekly = raw.get("weekly_token_cap", DEFAULT_WEEKLY_TOKEN_CAP)
    threshold = raw.get("warning_threshold", DEFAULT_WARNING_THRESHOLD)
    try:
        daily_int = max(0, int(daily))
    except (TypeError, ValueError):
        daily_int = DEFAULT_DAILY_TOKEN_CAP
    try:
        weekly_int = max(0, int(weekly))
    except (TypeError, ValueError):
        weekly_int = DEFAULT_WEEKLY_TOKEN_CAP
    try:
        threshold_float = float(threshold)
    except (TypeError, ValueError):
        threshold_float = DEFAULT_WARNING_THRESHOLD
    threshold_float = min(0.95, max(0.5, threshold_float))
    return daily_int, weekly_int, threshold_float


def _usage_sum(db: Session, user_id: int, start_at: datetime) -> int:
    value = db.scalar(
        select(func.coalesce(func.sum(AIUsageEvent.total_tokens), 0)).where(
            AIUsageEvent.user_id == user_id,
            AIUsageEvent.created_at >= start_at,
        )
    )
    return int(value or 0)


def get_usage_budget_snapshot(db: Session, user_id: int) -> UsageBudgetSnapshot:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    daily_cap, weekly_cap, threshold = _extract_budget_preferences(profile.preferences if profile else None)
    now = _utc_now()
    day_start = _day_start(now)
    week_start = _week_start(now)
    daily_used = _usage_sum(db, user_id, day_start)
    weekly_used = _usage_sum(db, user_id, week_start)
    daily_remaining = max(daily_cap - daily_used, 0)
    weekly_remaining = max(weekly_cap - weekly_used, 0)
    daily_warning = daily_cap > 0 and daily_used >= int(daily_cap * threshold)
    weekly_warning = weekly_cap > 0 and weekly_used >= int(weekly_cap * threshold)
    blocked = (daily_cap > 0 and daily_used >= daily_cap) or (weekly_cap > 0 and weekly_used >= weekly_cap)
    return UsageBudgetSnapshot(
        daily_token_cap=daily_cap,
        weekly_token_cap=weekly_cap,
        warning_threshold=threshold,
        daily_used_tokens=daily_used,
        weekly_used_tokens=weekly_used,
        daily_remaining_tokens=daily_remaining,
        weekly_remaining_tokens=weekly_remaining,
        daily_warning=daily_warning,
        weekly_warning=weekly_warning,
        blocked=blocked,
    )


def upsert_usage_budget_settings(
    db: Session,
    *,
    user_id: int,
    daily_token_cap: int,
    weekly_token_cap: int,
    warning_threshold: float,
) -> UsageBudgetSnapshot:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    if profile is None:
        raise ValueError("Learner profile not found")
    preferences = dict(profile.preferences or {})
    preferences["usage_budget"] = {
        "daily_token_cap": max(0, int(daily_token_cap)),
        "weekly_token_cap": max(0, int(weekly_token_cap)),
        "warning_threshold": min(0.95, max(0.5, float(warning_threshold))),
    }
    profile.preferences = preferences
    db.commit()
    db.refresh(profile)
    return get_usage_budget_snapshot(db, user_id)


def record_usage_event(
    db: Session,
    *,
    user_id: int,
    scope: str,
    model: str,
    prompt_tokens: int,
    output_tokens: int,
) -> None:
    total_tokens = max(0, int(prompt_tokens) + int(output_tokens))
    db.add(
        AIUsageEvent(
            user_id=user_id,
            scope=scope,
            model=model,
            prompt_tokens=max(0, int(prompt_tokens)),
            output_tokens=max(0, int(output_tokens)),
            total_tokens=total_tokens,
        )
    )
