import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState, LoadingState } from "../components/feedback";
import { useAppStore } from "../store/app-store";

export function SessionPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const dailyMinutes = useAppStore((s) => s.dailyMinutes);
  const [activeIndex, setActiveIndex] = useState(0);
  const session = useQuery({
    queryKey: ["coach-session-today", userId, dailyMinutes],
    queryFn: () => api.coachSessionToday(userId, dailyMinutes),
  });

  const activeStep = useMemo(() => {
    if (!session.data) return null;
    return session.data.steps[activeIndex] ?? null;
  }, [session.data, activeIndex]);

  return (
    <section className="panel stack">
      <h2>Daily Session</h2>
      <p>Run one guided cycle: warmup, coaching, drills, vocab review, and recap.</p>
      {session.isPending && <LoadingState text="Preparing your session..." />}
      {session.isError && <ErrorState text="Failed to load daily session." />}
      {session.isSuccess && (
        <>
          <p>
            Time budget: {session.data.time_budget_minutes} min | Focus: {session.data.focus.join(", ")}
          </p>
          <article className="panel">
            <h3>
              Step {activeIndex + 1}: {activeStep?.title}
            </h3>
            <p>{activeStep?.description}</p>
            <p>Recommended time: {activeStep?.duration_minutes} min</p>
            {activeStep && (
              <Link to={activeStep.route}>
                <button type="button">Open activity</button>
              </Link>
            )}
          </article>
          <div className="row">
            <button type="button" disabled={activeIndex === 0} onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}>
              Previous step
            </button>
            <button
              type="button"
              disabled={activeIndex >= session.data.steps.length - 1}
              onClick={() => setActiveIndex((i) => Math.min(session.data.steps.length - 1, i + 1))}
            >
              Next step
            </button>
          </div>
          <article className="panel">
            <h3>Session roadmap</h3>
            {session.data.steps.map((step, index) => (
              <p key={step.id}>
                {index + 1}. {step.title} ({step.duration_minutes} min)
              </p>
            ))}
          </article>
        </>
      )}
    </section>
  );
}
