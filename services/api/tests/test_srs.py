from datetime import UTC, datetime

from app.services.srs import next_srs_state


def test_srs_good_increases_interval() -> None:
    now = datetime(2026, 3, 5, tzinfo=UTC)
    result = next_srs_state(interval_days=2, ease=2.5, rating="good", now=now)
    assert result.interval_days >= 5
    assert result.ease >= 2.5
    assert result.due_at > now


def test_srs_again_resets_interval() -> None:
    now = datetime(2026, 3, 5, tzinfo=UTC)
    result = next_srs_state(interval_days=7, ease=2.4, rating="again", now=now)
    assert result.interval_days == 1
    assert result.ease < 2.4
