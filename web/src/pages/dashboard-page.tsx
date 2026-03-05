import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { useAppStore } from "../store/app-store";

export function DashboardPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const summary = useQuery({
    queryKey: ["summary", userId],
    queryFn: () => api.progressSummary(userId),
  });
  const plan = useQuery({
    queryKey: ["plan-today", userId],
    queryFn: () => api.planToday(userId, 15),
  });

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
