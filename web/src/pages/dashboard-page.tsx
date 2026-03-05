import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function DashboardPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
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
