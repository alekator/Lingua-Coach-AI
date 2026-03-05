import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function DashboardPage() {
  const navigate = useNavigate();
  const userId = useAppStore((s) => s.userId) ?? 1;
  const setDailyMinutes = useAppStore((s) => s.setDailyMinutes);
  const pushToast = useToastStore((s) => s.push);
  const [goalMinutes, setGoalMinutes] = useState(120);
  const [goalError, setGoalError] = useState("");
  const summary = useQuery({
    queryKey: ["summary", userId],
    queryFn: () => api.progressSummary(userId),
  });
  const weeklyGoal = useQuery({
    queryKey: ["weekly-goal", userId],
    queryFn: () => api.progressWeeklyGoal(userId),
  });
  const plan = useQuery({
    queryKey: ["plan-today", userId],
    queryFn: () => api.planToday(userId, 15),
  });
  const nextActions = useQuery({
    queryKey: ["coach-next-actions", userId],
    queryFn: () => api.coachNextActions(userId),
  });
  const reactivation = useQuery({
    queryKey: ["coach-reactivation", userId],
    queryFn: () => api.coachReactivation(userId),
  });
  const rewards = useQuery({
    queryKey: ["progress-rewards", userId],
    queryFn: () => api.progressRewards(userId),
  });
  const weeklyReview = useQuery({
    queryKey: ["progress-weekly-review", userId],
    queryFn: () => api.progressWeeklyReview(userId),
  });

  async function onSaveGoal() {
    try {
      await api.progressWeeklyGoalSet({ user_id: userId, target_minutes: goalMinutes });
      setGoalError("");
      pushToast("success", "Weekly goal updated");
      await weeklyGoal.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setGoalError(msg);
      pushToast("error", msg);
    }
  }

  async function onClaimReward(rewardId: string) {
    try {
      await api.progressRewardsClaim({ user_id: userId, reward_id: rewardId });
      pushToast("success", "Reward claimed");
      await rewards.refetch();
    } catch (err) {
      pushToast("error", getErrorMessage(err));
    }
  }

  function startFiveMinuteMode() {
    setDailyMinutes(5);
    pushToast("info", "5-minute mode enabled for today");
    navigate("/app/session");
  }

  const nextBestAction = nextActions.data?.items?.[0] ?? null;
  const reactivationMsg =
    reactivation.data && reactivation.data.eligible
      ? `You had a ${reactivation.data.gap_days}-day pause. ${reactivation.data.note}`
      : null;

  return (
    <section className="panel">
      <h2>Dashboard</h2>
      <p>Your coaching loop for today. Follow the plan, then track improvement in Profile.</p>
      {summary.isPending && <LoadingState text="Loading progress..." />}
      {summary.isError && <ErrorState text="Failed to load progress summary." />}
      {summary.isSuccess && summary.data.minutes_practiced === 0 && (
        <EmptyState text="No study activity yet. Start chat, voice, or exercises." />
      )}
      {summary.isSuccess && (
        <div className="grid">
          <article>
            <h3>Streak</h3>
            <p>{summary.data.streak_days} days</p>
          </article>
          <article>
            <h3>Practice Time</h3>
            <p>{summary.data.minutes_practiced} minutes</p>
          </article>
          <article>
            <h3>Words Learned</h3>
            <p>{summary.data.words_learned}</p>
          </article>
        </div>
      )}
      {weeklyGoal.isPending && <LoadingState text="Loading weekly goal..." />}
      {weeklyGoal.isError && <ErrorState text="Failed to load weekly goal." />}
      {weeklyGoal.isSuccess && (
        <article className="panel stack">
          <h3>Weekly Goal Tracker</h3>
          <p>
            Progress: {weeklyGoal.data.completed_minutes}/{weeklyGoal.data.target_minutes} min (
            {weeklyGoal.data.completion_percent}%)
          </p>
          <p>
            {weeklyGoal.data.is_completed
              ? "Goal completed for this week. Keep momentum."
              : `Remaining: ${weeklyGoal.data.remaining_minutes} min`}
          </p>
          <label>
            Set weekly goal (minutes)
            <input
              type="number"
              min={30}
              max={2000}
              value={goalMinutes}
              onChange={(e) => setGoalMinutes(Number(e.target.value || 120))}
            />
          </label>
          <button type="button" onClick={onSaveGoal}>
            Save weekly goal
          </button>
          {goalError && <ErrorState text={goalError} />}
        </article>
      )}
      {nextActions.isPending && <LoadingState text="Loading coach next actions..." />}
      {nextActions.isError && <ErrorState text="Failed to load coach next actions." />}
      {nextActions.isSuccess && (
        <article className="panel stack">
          <h3>Coach Next Actions</h3>
          {nextBestAction && (
            <div className="panel stack">
              <p>
                <strong>Today one step:</strong> {nextBestAction.title}
              </p>
              <p>{nextBestAction.reason}</p>
              <Link to={nextBestAction.route}>
                <button type="button">Do next best action</button>
              </Link>
              <button type="button" onClick={startFiveMinuteMode}>
                Start 5-minute mode
              </button>
              {reactivationMsg && <p>Reactivation: {reactivationMsg}</p>}
            </div>
          )}
          {nextActions.data.items.map((item) => (
            <div key={item.id} className="panel stack">
              <p>
                <strong>{item.title}</strong>
              </p>
              <p>{item.reason}</p>
              <Link to={item.route}>
                <button type="button">Open action</button>
              </Link>
            </div>
          ))}
        </article>
      )}
      {reactivation.isSuccess && reactivation.data.eligible && (
        <article className="panel stack">
          <h3>Easy Return Plan</h3>
          <p>{reactivation.data.title}</p>
          {reactivation.data.weak_topic && <p>Focus area: {reactivation.data.weak_topic}</p>}
          {reactivation.data.tasks.map((task) => (
            <p key={task}>- {task}</p>
          ))}
          <button type="button" onClick={startFiveMinuteMode}>
            Start easy return (5 min)
          </button>
        </article>
      )}
      {rewards.isPending && <LoadingState text="Loading rewards..." />}
      {rewards.isError && <ErrorState text="Failed to load rewards." />}
      {rewards.isSuccess && (
        <article className="panel stack">
          <h3>Rewards</h3>
          <p>
            XP: {rewards.data.total_xp} | Claimed: {rewards.data.claimed_count}
          </p>
          {rewards.data.items.map((item) => (
            <div key={item.id} className="panel stack">
              <p>
                <strong>{item.title}</strong> ({item.xp_points} XP)
              </p>
              <p>{item.description}</p>
              <p>Requirement: {item.requirement}</p>
              {item.status === "available" && (
                <button type="button" onClick={() => onClaimReward(item.id)}>
                  Claim reward
                </button>
              )}
              {item.status === "claimed" && <p>Status: claimed</p>}
              {item.status === "locked" && <p>Status: locked</p>}
            </div>
          ))}
        </article>
      )}
      {weeklyReview.isPending && <LoadingState text="Loading weekly review..." />}
      {weeklyReview.isError && <ErrorState text="Failed to load weekly review." />}
      {weeklyReview.isSuccess && (
        <article className="panel stack">
          <h3>Weekly Review</h3>
          <p>
            Sessions: {weeklyReview.data.weekly_sessions} | Minutes: {weeklyReview.data.weekly_minutes}
          </p>
          <p>
            Goal: {weeklyReview.data.weekly_goal_target_minutes} min{" "}
            {weeklyReview.data.weekly_goal_completed ? "(completed)" : "(in progress)"}
          </p>
          <p>
            Skills: strongest {weeklyReview.data.strongest_skill}, weakest {weeklyReview.data.weakest_skill}
          </p>
          {weeklyReview.data.top_weak_area && <p>Most frequent weak area: {weeklyReview.data.top_weak_area}</p>}
          {weeklyReview.data.wins.map((win) => (
            <p key={win}>- {win}</p>
          ))}
          <p>Next focus: {weeklyReview.data.next_focus}</p>
        </article>
      )}
      {plan.isPending && <LoadingState text="Generating today plan..." />}
      {plan.isError && <ErrorState text="Failed to load daily plan." />}
      {plan.isSuccess && (
        <article className="panel">
          <h3>Today Coaching Plan ({plan.data.time_budget_minutes} min)</h3>
          <p>Focus pillars: {plan.data.focus.join(", ")}</p>
          {plan.data.adaptation_notes.map((note) => (
            <p key={note}>Adaptation: {note}</p>
          ))}
          {plan.data.tasks.map((task) => (
            <p key={task}>- {task}</p>
          ))}
          <Link to="/app/session">
            <button type="button">Start today session</button>
          </Link>
        </article>
      )}
    </section>
  );
}
