from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC


@dataclass(frozen=True)
class SrsResult:
    interval_days: int
    ease: float
    due_at: datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def next_srs_state(interval_days: int, ease: float, rating: str, now: datetime | None = None) -> SrsResult:
    now = now or utcnow()
    if rating == "again":
        new_interval = 1
        new_ease = max(1.3, ease - 0.2)
    elif rating == "hard":
        new_interval = max(1, int(round(interval_days * 1.2)))
        new_ease = max(1.3, ease - 0.15)
    elif rating == "good":
        new_interval = max(1, int(round(interval_days * ease)))
        new_ease = min(2.8, ease + 0.05)
    elif rating == "easy":
        new_interval = max(1, int(round(interval_days * ease * 1.4)))
        new_ease = min(3.0, ease + 0.1)
    else:
        raise ValueError("Unsupported SRS rating")

    return SrsResult(
        interval_days=new_interval,
        ease=round(new_ease, 2),
        due_at=now + timedelta(days=new_interval),
    )
