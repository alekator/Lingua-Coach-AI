import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
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
      {summary.isPending && <p>Loading progress...</p>}
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
      {plan.isSuccess && (
        <article className="panel">
          <h3>Today Plan ({plan.data.time_budget_minutes} min)</h3>
          <p>Focus: {plan.data.focus.join(", ")}</p>
          {plan.data.tasks.map((task) => (
            <p key={task}>- {task}</p>
          ))}
        </article>
      )}
    </section>
  );
}
