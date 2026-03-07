import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function SessionPage() {
  const queryClient = useQueryClient();
  const userId = useAppStore((s) => s.userId) ?? 1;
  const dailyMinutes = useAppStore((s) => s.dailyMinutes);
  const [activeIndex, setActiveIndex] = useState(0);
  const [actionError, setActionError] = useState("");
  const [updating, setUpdating] = useState(false);
  const pushToast = useToastStore((s) => s.push);
  const session = useQuery({
    queryKey: ["coach-session-today", userId, dailyMinutes],
    queryFn: () => api.coachSessionToday(userId, dailyMinutes),
  });
  const progress = useQuery({
    queryKey: ["coach-session-progress", userId, dailyMinutes],
    queryFn: () => api.coachSessionProgress(userId, dailyMinutes),
  });

  const activeStep = useMemo(() => {
    if (!session.data) return null;
    return session.data.steps[activeIndex] ?? null;
  }, [session.data, activeIndex]);

  const statusByStep = useMemo(() => {
    const map = new Map<string, "pending" | "in_progress" | "completed">();
    for (const item of progress.data?.items ?? []) {
      map.set(item.step_id, item.status);
    }
    return map;
  }, [progress.data]);

  useEffect(() => {
    if (!session.data || !progress.data) return;
    const firstOpenIndex = session.data.steps.findIndex((step) => statusByStep.get(step.id) !== "completed");
    if (firstOpenIndex >= 0) {
      setActiveIndex(firstOpenIndex);
    }
  }, [session.data, progress.data, statusByStep]);

  async function markStep(status: "in_progress" | "completed") {
    if (!activeStep) return;
    setUpdating(true);
    try {
      await api.coachSessionProgressUpsert({
        user_id: userId,
        step_id: activeStep.id,
        status,
        time_budget_minutes: dailyMinutes,
      });
      await queryClient.invalidateQueries({ queryKey: ["coach-session-progress", userId, dailyMinutes] });
      setActionError("");
      pushToast("success", status === "completed" ? "Step marked as completed" : "Step started");
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    } finally {
      setUpdating(false);
    }
  }

  return (
    <section className="session-page stack">
      <article className="panel session-hero">
        <div>
          <h2>Coach Session</h2>
          <p>Follow your guided flow: warmup, focused practice, quick drill, vocab review, and recap.</p>
        </div>
        {progress.data && (
          <div className="session-hero-kpis">
            <span className="badge">Steps: {progress.data.total_steps}</span>
            <span className="badge">Done: {progress.data.completed_steps}</span>
            <span className="badge">Progress: {progress.data.completion_percent}%</span>
          </div>
        )}
      </article>

      {session.isPending && <LoadingState text="Preparing your session..." />}
      {session.isError && <ErrorState text="Failed to load daily session." />}
      {progress.isPending && <LoadingState text="Loading session progress..." />}
      {progress.isError && <ErrorState text="Failed to load session progress." />}
      {session.isSuccess && (
        <>
          <section className="session-grid">
            <article className="panel session-main-card stack">
              <div className="session-meta-row">
                <p>
                  Time budget: {session.data.time_budget_minutes} min | Focus: {session.data.focus.join(", ")}
                </p>
                <p>Coach note: complete each step in order, even if you keep responses short.</p>
              </div>
              {progress.data && (
                <div className="session-progress-strip">
                  <p>
                    Progress: {progress.data.completed_steps}/{progress.data.total_steps} steps ({progress.data.completion_percent}
                    %)
                  </p>
                  <div className="progress-meter" aria-hidden>
                    <span style={{ width: `${progress.data.completion_percent}%` }} />
                  </div>
                </div>
              )}

              <article className="session-active-step">
                <h3>
                  Step {activeIndex + 1}: {activeStep?.title}
                </h3>
                <p>{activeStep?.description}</p>
                <p>Recommended time: {activeStep?.duration_minutes} min</p>
                {activeStep && <p>Status: {statusByStep.get(activeStep.id) ?? "pending"}</p>}
                <div className="row">
                  {activeStep && (
                    <Link to={activeStep.route}>
                      <button type="button" className="cta-secondary">
                        Open activity
                      </button>
                    </Link>
                  )}
                  <button
                    type="button"
                    className="cta-secondary"
                    onClick={() => markStep("in_progress")}
                    disabled={!activeStep || updating || (activeStep ? statusByStep.get(activeStep.id) === "completed" : true)}
                  >
                    Mark step started
                  </button>
                  <button
                    type="button"
                    onClick={() => markStep("completed")}
                    disabled={!activeStep || updating || (activeStep ? statusByStep.get(activeStep.id) === "completed" : true)}
                  >
                    Mark step completed
                  </button>
                </div>
              </article>

              {actionError && <ErrorState text={actionError} />}

              <div className="row">
                <button
                  type="button"
                  className="cta-secondary"
                  disabled={activeIndex === 0}
                  onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}
                >
                  Previous step
                </button>
                <button
                  type="button"
                  className="cta-secondary"
                  disabled={activeIndex >= session.data.steps.length - 1}
                  onClick={() => setActiveIndex((i) => Math.min(session.data.steps.length - 1, i + 1))}
                >
                  Next step
                </button>
              </div>
            </article>

            <aside className="panel session-roadmap-card stack">
              <h3>Today step roadmap</h3>
              <section className="session-roadmap-list">
                {session.data.steps.map((step, index) => {
                  const status = statusByStep.get(step.id) ?? "pending";
                  const isActive = index === activeIndex;
                  return (
                    <article key={step.id} className={`session-roadmap-item ${status} ${isActive ? "active" : ""}`}>
                      <p>
                        {index + 1}. {step.title}
                      </p>
                      <small>
                        {step.duration_minutes} min | {status}
                      </small>
                    </article>
                  );
                })}
              </section>
            </aside>
          </section>
        </>
      )}
    </section>
  );
}
