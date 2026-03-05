from datetime import date

from app.services.progress import compute_streak_days


def test_compute_streak_days_contiguous() -> None:
    days = [date(2026, 3, 3), date(2026, 3, 4), date(2026, 3, 5)]
    streak = compute_streak_days(days, today=date(2026, 3, 5))
    assert streak == 3


def test_compute_streak_days_broken() -> None:
    days = [date(2026, 3, 1), date(2026, 3, 3), date(2026, 3, 5)]
    streak = compute_streak_days(days, today=date(2026, 3, 5))
    assert streak == 1
