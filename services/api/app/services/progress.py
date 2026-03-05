from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def compute_streak_days(active_dates: list[date], today: date | None = None) -> int:
    if not active_dates:
        return 0
    days = sorted(set(active_dates))
    today = today or datetime.now(UTC).date()
    if days[-1] < today - timedelta(days=1):
        return 0

    streak = 0
    cursor = days[-1]
    day_set = set(days)
    while cursor in day_set:
        streak += 1
        cursor = cursor - timedelta(days=1)
    return streak
