from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatSession, LearnerProfile, Message, Mistake, SkillSnapshot, SrsState, User, VocabItem
from app.schemas.progress import (
    ProgressJournalEntry,
    ProgressJournalResponse,
    ProgressRewardsResponse,
    ProgressSkillMapResponse,
    ProgressStreakResponse,
    ProgressSummaryResponse,
    ProgressWeeklyReviewResponse,
    ProgressOutcomesResponse,
    RewardClaimRequest,
    RewardItem,
    WeeklyGoalResponse,
    WeeklyGoalSetRequest,
)
from app.services.progress import compute_streak_days

router = APIRouter(prefix="/progress", tags=["progress"])
DEFAULT_WEEKLY_GOAL_MINUTES = 90
REWARD_DEFINITIONS = (
    {
        "id": "streak_3",
        "title": "3-Day Streak",
        "description": "You studied 3 days in a row.",
        "requirement": "Reach a 3-day streak",
        "xp_points": 30,
    },
    {
        "id": "streak_7",
        "title": "7-Day Streak",
        "description": "You studied 7 days in a row.",
        "requirement": "Reach a 7-day streak",
        "xp_points": 90,
    },
    {
        "id": "weekly_goal_complete",
        "title": "Weekly Goal Complete",
        "description": "You completed your weekly minutes target.",
        "requirement": "Complete weekly goal",
        "xp_points": 60,
    },
)


def _to_utc_date(dt: datetime) -> datetime.date:
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(UTC).date()


def _to_utc_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _get_weekly_sessions(user_id: int, db: Session) -> list[ChatSession]:
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    cutoff = datetime.now(UTC) - timedelta(days=7)
    return [s for s in sessions if s.started_at and _to_utc_datetime(s.started_at) >= cutoff]


def _read_weekly_goal_target(profile: LearnerProfile | None) -> int:
    if not profile:
        return DEFAULT_WEEKLY_GOAL_MINUTES
    raw = (profile.preferences or {}).get("weekly_goal_minutes")
    if isinstance(raw, int) and raw >= 30:
        return raw
    return DEFAULT_WEEKLY_GOAL_MINUTES


def _read_reward_claims(profile: LearnerProfile | None) -> set[str]:
    if not profile:
        return set()
    raw = (profile.preferences or {}).get("reward_claims")
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw if isinstance(item, str)}


def _reward_unlocked(reward_id: str, *, streak_days: int, weekly_goal_completed: bool) -> bool:
    if reward_id == "streak_3":
        return streak_days >= 3
    if reward_id == "streak_7":
        return streak_days >= 7
    if reward_id == "weekly_goal_complete":
        return weekly_goal_completed
    return False


def _build_rewards(user_id: int, db: Session) -> ProgressRewardsResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    streak = progress_streak(user_id=user_id, db=db)
    weekly_goal = progress_weekly_goal(user_id=user_id, db=db)
    claimed_ids = _read_reward_claims(profile)
    items: list[RewardItem] = []
    claimed_count = 0
    total_xp = 0

    for reward in REWARD_DEFINITIONS:
        reward_id = reward["id"]
        unlocked = _reward_unlocked(
            reward_id,
            streak_days=streak.streak_days,
            weekly_goal_completed=weekly_goal.is_completed,
        )
        if reward_id in claimed_ids:
            status = "claimed"
            claimed_count += 1
            total_xp += int(reward["xp_points"])
        elif unlocked:
            status = "available"
        else:
            status = "locked"
        items.append(RewardItem(status=status, **reward))

    return ProgressRewardsResponse(
        user_id=user_id,
        total_xp=total_xp,
        claimed_count=claimed_count,
        items=items,
    )


def _get_or_create_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user:
        return user
    user = User(id=user_id)
    db.add(user)
    db.flush()
    return user


def _score_to_cefr_from_skills(score: float) -> str:
    if score < 25:
        return "A1"
    if score < 40:
        return "A2"
    if score < 55:
        return "B1"
    if score < 70:
        return "B2"
    if score < 85:
        return "C1"
    return "C2"


@router.get("/skill-map", response_model=ProgressSkillMapResponse)
def progress_skill_map(user_id: int, db: Session = Depends(get_db)) -> ProgressSkillMapResponse:
    snapshot = db.scalars(
        select(SkillSnapshot)
        .where(SkillSnapshot.user_id == user_id)
        .order_by(SkillSnapshot.created_at.desc())
    ).first()
    if not snapshot:
        return ProgressSkillMapResponse(
            speaking=0.0,
            listening=0.0,
            grammar=0.0,
            vocab=0.0,
            reading=0.0,
            writing=0.0,
        )
    return ProgressSkillMapResponse(
        speaking=snapshot.speaking,
        listening=snapshot.listening,
        grammar=snapshot.grammar,
        vocab=snapshot.vocab,
        reading=snapshot.reading,
        writing=snapshot.writing,
    )


@router.get("/streak", response_model=ProgressStreakResponse)
def progress_streak(user_id: int, db: Session = Depends(get_db)) -> ProgressStreakResponse:
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    active_dates = sorted({_to_utc_date(s.started_at) for s in sessions if s.started_at})
    streak = compute_streak_days(active_dates)
    return ProgressStreakResponse(streak_days=streak, active_dates=active_dates)


@router.get("/summary", response_model=ProgressSummaryResponse)
def progress_summary(user_id: int, db: Session = Depends(get_db)) -> ProgressSummaryResponse:
    words_learned = len(db.scalars(select(VocabItem).where(VocabItem.user_id == user_id)).all())
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user_id)).all()
    minutes_practiced = len(sessions) * 8

    active_dates = sorted({_to_utc_date(s.started_at) for s in sessions if s.started_at})
    streak = compute_streak_days(active_dates)

    skill = progress_skill_map(user_id=user_id, db=db)
    return ProgressSummaryResponse(
        streak_days=streak,
        minutes_practiced=minutes_practiced,
        words_learned=words_learned,
        speaking=skill.speaking,
        listening=skill.listening,
        grammar=skill.grammar,
        vocab=skill.vocab,
        reading=skill.reading,
        writing=skill.writing,
    )


@router.get("/weekly-review", response_model=ProgressWeeklyReviewResponse)
def progress_weekly_review(user_id: int, db: Session = Depends(get_db)) -> ProgressWeeklyReviewResponse:
    weekly_goal = progress_weekly_goal(user_id=user_id, db=db)
    streak = progress_streak(user_id=user_id, db=db)
    journal = progress_journal(user_id=user_id, db=db)
    summary = progress_summary(user_id=user_id, db=db)

    skill_map = {
        "speaking": summary.speaking,
        "listening": summary.listening,
        "grammar": summary.grammar,
        "vocab": summary.vocab,
        "reading": summary.reading,
        "writing": summary.writing,
    }
    strongest_skill = max(skill_map.items(), key=lambda item: item[1])[0]
    weakest_skill = min(skill_map.items(), key=lambda item: item[1])[0]
    top_weak_area = journal.weak_areas[0] if journal.weak_areas else None

    wins = [
        f"{journal.weekly_sessions} sessions completed this week.",
        f"{journal.weekly_minutes} active learning minutes logged.",
    ]
    if streak.streak_days >= 2:
        wins.append(f"Current streak: {streak.streak_days} days.")
    if weekly_goal.is_completed:
        wins.append("Weekly goal reached.")

    next_focus = (
        f"Keep momentum with one short drill in {top_weak_area or weakest_skill} and one coach chat turn."
    )

    return ProgressWeeklyReviewResponse(
        user_id=user_id,
        weekly_minutes=journal.weekly_minutes,
        weekly_sessions=journal.weekly_sessions,
        weekly_goal_target_minutes=weekly_goal.target_minutes,
        weekly_goal_completed=weekly_goal.is_completed,
        streak_days=streak.streak_days,
        strongest_skill=strongest_skill,
        weakest_skill=weakest_skill,
        top_weak_area=top_weak_area,
        wins=wins,
        next_focus=next_focus,
    )


@router.get("/outcomes", response_model=ProgressOutcomesResponse)
def progress_outcomes(user_id: int, db: Session = Depends(get_db)) -> ProgressOutcomesResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    current_level = profile.level if profile else "A1"

    snapshots = db.scalars(
        select(SkillSnapshot).where(SkillSnapshot.user_id == user_id).order_by(SkillSnapshot.created_at.asc())
    ).all()
    if snapshots:
        latest = snapshots[-1]
        avg_skill = round(
            (latest.speaking + latest.listening + latest.grammar + latest.vocab + latest.reading + latest.writing)
            / 6.0,
            2,
        )
    else:
        avg_skill = 0.0

    cutoff = datetime.now(UTC) - timedelta(days=7)
    week_snapshots = [s for s in snapshots if s.created_at and _to_utc_datetime(s.created_at) >= cutoff]
    if len(week_snapshots) >= 2:
        first_week = week_snapshots[0]
        last_week = week_snapshots[-1]
        first_avg = (
            first_week.speaking
            + first_week.listening
            + first_week.grammar
            + first_week.vocab
            + first_week.reading
            + first_week.writing
        ) / 6.0
        last_avg = (
            last_week.speaking
            + last_week.listening
            + last_week.grammar
            + last_week.vocab
            + last_week.reading
            + last_week.writing
        ) / 6.0
        improvement_7d = round(last_avg - first_avg, 2)
    else:
        improvement_7d = 0.0

    journal = progress_journal(user_id=user_id, db=db)
    streak = progress_streak(user_id=user_id, db=db)
    estimated_level = _score_to_cefr_from_skills(avg_skill)

    if len(snapshots) >= 6 and journal.weekly_sessions >= 3:
        confidence = "high"
    elif len(snapshots) >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    recommendations: list[str] = []
    if improvement_7d <= 0:
        recommendations.append("Keep daily 5-minute consistency to rebuild improvement trend.")
    if journal.weak_areas:
        recommendations.append(f"Prioritize one focused drill for: {journal.weak_areas[0]}.")
    if streak.streak_days < 2:
        recommendations.append("Aim for a 2-day streak this week before increasing intensity.")
    if not recommendations:
        recommendations.append("Good trajectory. Keep current pace and increase complexity gradually.")

    return ProgressOutcomesResponse(
        user_id=user_id,
        current_level=current_level,
        estimated_level_from_skills=estimated_level,
        avg_skill_score=avg_skill,
        improvement_7d_points=improvement_7d,
        weekly_sessions=journal.weekly_sessions,
        streak_days=streak.streak_days,
        confidence=confidence,
        recommendations=recommendations[:3],
    )


@router.get("/journal", response_model=ProgressJournalResponse)
def progress_journal(user_id: int, db: Session = Depends(get_db)) -> ProgressJournalResponse:
    sessions = db.scalars(
        select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.started_at.desc())
    ).all()
    weekly_sessions = _get_weekly_sessions(user_id, db)

    message_counts = dict(
        db.execute(
            select(Message.session_id, func.count(Message.id))
            .join(ChatSession, ChatSession.id == Message.session_id)
            .where(ChatSession.user_id == user_id)
            .group_by(Message.session_id)
        ).all()
    )
    entries = [
        ProgressJournalEntry(
            session_id=s.id,
            started_at=_to_utc_date(s.started_at),
            mode=s.mode,
            messages_count=int(message_counts.get(s.id, 0)),
            completed=s.ended_at is not None,
        )
        for s in sessions[:15]
    ]

    mistakes = db.scalars(
        select(Mistake).where(Mistake.user_id == user_id).order_by(Mistake.created_at.desc()).limit(100)
    ).all()
    weak_areas = [name for name, _ in Counter(m.category for m in mistakes if m.category).most_common(3)]

    due_vocab_count = db.scalar(
        select(func.count(SrsState.vocab_item_id))
        .select_from(SrsState)
        .join(VocabItem, VocabItem.id == SrsState.vocab_item_id)
        .where(VocabItem.user_id == user_id, SrsState.due_at <= datetime.now(UTC))
    )
    next_actions: list[str] = []
    if due_vocab_count and due_vocab_count > 0:
        next_actions.append(f"Review due vocabulary cards ({int(due_vocab_count)}).")
    if weak_areas:
        next_actions.append(f"Run one targeted drill for: {weak_areas[0]}.")
    if len(weekly_sessions) < 3:
        next_actions.append("Add one short coach chat session today to keep momentum.")
    if not next_actions:
        next_actions.append("Great consistency. Keep the daily session cadence.")

    return ProgressJournalResponse(
        weekly_minutes=len(weekly_sessions) * 8,
        weekly_sessions=len(weekly_sessions),
        weak_areas=weak_areas,
        next_actions=next_actions,
        entries=entries,
    )


@router.get("/weekly-goal", response_model=WeeklyGoalResponse)
def progress_weekly_goal(user_id: int, db: Session = Depends(get_db)) -> WeeklyGoalResponse:
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    target_minutes = _read_weekly_goal_target(profile)
    completed_minutes = len(_get_weekly_sessions(user_id, db)) * 8
    remaining_minutes = max(0, target_minutes - completed_minutes)
    completion_percent = min(100, round((completed_minutes / max(1, target_minutes)) * 100))
    return WeeklyGoalResponse(
        user_id=user_id,
        target_minutes=target_minutes,
        completed_minutes=completed_minutes,
        remaining_minutes=remaining_minutes,
        completion_percent=completion_percent,
        is_completed=completed_minutes >= target_minutes,
    )


@router.post("/weekly-goal", response_model=WeeklyGoalResponse)
def progress_weekly_goal_set(payload: WeeklyGoalSetRequest, db: Session = Depends(get_db)) -> WeeklyGoalResponse:
    _get_or_create_user(db, payload.user_id)
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == payload.user_id))
    if profile is None:
        profile = LearnerProfile(
            user_id=payload.user_id,
            native_lang="ru",
            target_lang="en",
            level="A1",
            goal=None,
            preferences={"weekly_goal_minutes": payload.target_minutes},
        )
        db.add(profile)
    else:
        prefs = dict(profile.preferences or {})
        prefs["weekly_goal_minutes"] = payload.target_minutes
        profile.preferences = prefs
    db.commit()
    return progress_weekly_goal(user_id=payload.user_id, db=db)


@router.get("/rewards", response_model=ProgressRewardsResponse)
def progress_rewards(user_id: int, db: Session = Depends(get_db)) -> ProgressRewardsResponse:
    return _build_rewards(user_id=user_id, db=db)


@router.post("/rewards/claim", response_model=ProgressRewardsResponse)
def progress_rewards_claim(payload: RewardClaimRequest, db: Session = Depends(get_db)) -> ProgressRewardsResponse:
    _get_or_create_user(db, payload.user_id)
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == payload.user_id))
    if profile is None:
        profile = LearnerProfile(
            user_id=payload.user_id,
            native_lang="ru",
            target_lang="en",
            level="A1",
            goal=None,
            preferences={},
        )
        db.add(profile)

    rewards = _build_rewards(user_id=payload.user_id, db=db)
    item = next((reward for reward in rewards.items if reward.id == payload.reward_id), None)
    if item is None or item.status != "available":
        return rewards

    prefs = dict(profile.preferences or {})
    claimed = set(str(it) for it in prefs.get("reward_claims", []) if isinstance(it, str))
    claimed.add(payload.reward_id)
    prefs["reward_claims"] = sorted(claimed)
    profile.preferences = prefs
    db.commit()
    return _build_rewards(user_id=payload.user_id, db=db)
