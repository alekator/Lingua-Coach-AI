import { useQuery } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";
import type { HomeworkItem } from "../api/types";

function getPrimaryPrompt(item: HomeworkItem): string {
  const primary = item.tasks.find((task) => typeof task.prompt === "string");
  return typeof primary?.prompt === "string" ? primary.prompt : "";
}

export function HomeworkPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [actionError, setActionError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [answerDrafts, setAnswerDrafts] = useState<Record<number, string>>({});
  const [editDrafts, setEditDrafts] = useState<Record<number, { title: string; prompt: string; status: string }>>({});
  const pushToast = useToastStore((s) => s.push);
  const list = useQuery({
    queryKey: ["homework", userId],
    queryFn: () => api.homeworkList(userId),
  });

  const stats = useMemo(() => {
    const items = list.data?.items ?? [];
    const total = items.length;
    const submitted = items.filter((item) => item.status === "submitted").length;
    const assigned = items.filter((item) => item.status === "assigned").length;
    const inReview = items.filter((item) => item.status === "in_review").length;
    const completion = total > 0 ? Math.round((submitted / total) * 100) : 0;
    const scored = items.filter((item) => typeof item.latest_score === "number");
    const avgScore =
      scored.length > 0
        ? Math.round((scored.reduce((acc, item) => acc + (item.latest_score ?? 0), 0) / scored.length) * 100)
        : 0;
    return { total, submitted, assigned, inReview, completion, avgScore };
  }, [list.data?.items]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    const nextTitle = title.trim();
    const nextPrompt = prompt.trim();
    if (!nextTitle || !nextPrompt) {
      setActionError("Fill both homework title and assignment prompt.");
      return;
    }
    try {
      await api.homeworkCreate({
        user_id: userId,
        title: nextTitle,
        tasks: [
          { id: "response", type: "freeform", prompt: nextPrompt },
        ],
      });
      setTitle("");
      setPrompt("");
      setActionError("");
      pushToast("success", "Homework created");
      await list.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    }
  }

  async function onDelete(homeworkId: number) {
    setBusyId(homeworkId);
    try {
      await api.homeworkDelete(homeworkId);
      setAnswerDrafts((prev) => {
        const next = { ...prev };
        delete next[homeworkId];
        return next;
      });
      setEditDrafts((prev) => {
        const next = { ...prev };
        delete next[homeworkId];
        return next;
      });
      if (editingId === homeworkId) {
        setEditingId(null);
      }
      setActionError("");
      pushToast("success", "Homework deleted");
      await list.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    } finally {
      setBusyId(null);
    }
  }

  function startEdit(item: HomeworkItem) {
    setEditingId(item.id);
    setEditDrafts((prev) => ({
      ...prev,
      [item.id]: {
        title: item.title,
        prompt: getPrimaryPrompt(item),
        status: item.status,
      },
    }));
  }

  async function onSaveEdit(item: HomeworkItem) {
    const draft = editDrafts[item.id];
    if (!draft) return;
    const nextTitle = draft.title.trim();
    const nextPrompt = draft.prompt.trim();
    if (!nextTitle || !nextPrompt) {
      setActionError("Homework title and prompt cannot be empty.");
      return;
    }
    setBusyId(item.id);
    try {
      await api.homeworkUpdate(item.id, {
        title: nextTitle,
        tasks: [{ id: "response", type: "freeform", prompt: nextPrompt }],
        due_at: item.due_at ?? null,
        status: draft.status,
      });
      setEditingId(null);
      setActionError("");
      pushToast("success", "Homework updated");
      await list.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    } finally {
      setBusyId(null);
    }
  }

  async function onSubmit(homeworkId: number) {
    const answerText = (answerDrafts[homeworkId] ?? "").trim();
    if (!answerText) {
      setActionError("Type your homework answer before submitting.");
      return;
    }
    setBusyId(homeworkId);
    try {
      await api.homeworkSubmit({
        homework_id: homeworkId,
        answers: { response: answerText },
      });
      setActionError("");
      setAnswerDrafts((prev) => ({ ...prev, [homeworkId]: "" }));
      pushToast("success", "Homework submitted");
      await list.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="panel stack homework-page">
      <header className="homework-hero panel">
        <div>
          <h2>Coach Homework</h2>
          <p>Create polished assignments, write clear answers, and track delivery quality in one workflow.</p>
        </div>
      </header>
      <section className="homework-grid">
        <article className="panel stack homework-main-card">
          <form onSubmit={onCreate} className="stack homework-create-form">
            <h3>New Homework Card</h3>
            <label>
              Homework title
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Daily grammar drill" />
            </label>
            <label>
              Assignment prompt
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe what student should complete and submit."
                rows={3}
              />
            </label>
            <button type="submit" className="cta-primary">
              Create homework
            </button>
          </form>
          {actionError && <ErrorState text={actionError} />}
          {list.isPending && <LoadingState text="Loading homework..." />}
          {list.isError && <ErrorState text="Failed to load homework." />}
          {list.isSuccess && list.data.items.length === 0 && <EmptyState text="No homework yet." />}
          {list.isSuccess && (
            <div className="stack homework-cards">
              {list.data.items.map((item) => {
                const isEditing = editingId === item.id;
                const draft = editDrafts[item.id] ?? {
                  title: item.title,
                  prompt: getPrimaryPrompt(item),
                  status: item.status,
                };
                return (
                  <article key={item.id} className="panel homework-card">
                    <div className="homework-card-head">
                      <span className={`homework-status ${item.status}`}>{item.status.replace("_", " ")}</span>
                      <div className="homework-card-actions">
                        {!isEditing ? (
                          <button type="button" onClick={() => startEdit(item)} disabled={busyId === item.id}>
                            Edit
                          </button>
                        ) : (
                          <>
                            <button type="button" onClick={() => void onSaveEdit(item)} disabled={busyId === item.id}>
                              Save
                            </button>
                            <button type="button" onClick={() => setEditingId(null)} disabled={busyId === item.id}>
                              Cancel
                            </button>
                          </>
                        )}
                        <button type="button" onClick={() => void onDelete(item.id)} disabled={busyId === item.id}>
                          Delete
                        </button>
                      </div>
                    </div>
                    {!isEditing ? (
                      <>
                        <h3>{item.title}</h3>
                        <p className="homework-prompt">{getPrimaryPrompt(item) || "No prompt provided."}</p>
                      </>
                    ) : (
                      <div className="stack homework-edit-fields">
                        <label>
                          Title
                          <input
                            value={draft.title}
                            onChange={(e) =>
                              setEditDrafts((prev) => ({
                                ...prev,
                                [item.id]: { ...draft, title: e.target.value },
                              }))
                            }
                          />
                        </label>
                        <label>
                          Prompt
                          <textarea
                            value={draft.prompt}
                            rows={3}
                            onChange={(e) =>
                              setEditDrafts((prev) => ({
                                ...prev,
                                [item.id]: { ...draft, prompt: e.target.value },
                              }))
                            }
                          />
                        </label>
                        <label>
                          Status
                          <select
                            value={draft.status}
                            onChange={(e) =>
                              setEditDrafts((prev) => ({
                                ...prev,
                                [item.id]: { ...draft, status: e.target.value },
                              }))
                            }
                          >
                            <option value="assigned">assigned</option>
                            <option value="in_review">in review</option>
                            <option value="submitted">submitted</option>
                          </select>
                        </label>
                      </div>
                    )}
                    <div className="stack">
                      <label>
                        Your answer
                        <textarea
                          rows={4}
                          value={answerDrafts[item.id] ?? item.latest_answer_text ?? ""}
                          onChange={(e) =>
                            setAnswerDrafts((prev) => ({
                              ...prev,
                              [item.id]: e.target.value,
                            }))
                          }
                          placeholder="Write full homework answer before sending to coach."
                          disabled={item.status === "submitted" && !isEditing}
                        />
                      </label>
                      <div className="homework-submit-row">
                        <button
                          type="button"
                          className="cta-secondary"
                          onClick={() => void onSubmit(item.id)}
                          disabled={busyId === item.id || item.status === "submitted"}
                        >
                          {busyId === item.id ? "Submitting..." : item.status === "submitted" ? "Submitted" : "Submit to coach"}
                        </button>
                        {typeof item.latest_score === "number" && (
                          <span className="badge">Score: {Math.round(item.latest_score * 100)}%</span>
                        )}
                        {item.submission_count > 0 && <span className="badge">Submissions: {item.submission_count}</span>}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </article>
        <aside className="panel stack homework-progress-card" aria-live="polite">
          <h3>Homework Progress</h3>
          <div
            className="homework-progress-ring"
            role="img"
            aria-label={`Homework completion ${stats.completion}%`}
            style={{
              background: `conic-gradient(#22c55e ${stats.completion}%, color-mix(in srgb, var(--status-loading-bg) 42%, transparent) 0%)`,
            }}
          >
            <span>{stats.completion}%</span>
          </div>
          <div className="homework-progress-kpis">
            <article className="panel">
              <p>Total cards</p>
              <strong>{stats.total}</strong>
            </article>
            <article className="panel">
              <p>Submitted</p>
              <strong>{stats.submitted}</strong>
            </article>
            <article className="panel">
              <p>Assigned</p>
              <strong>{stats.assigned}</strong>
            </article>
            <article className="panel">
              <p>In review</p>
              <strong>{stats.inReview}</strong>
            </article>
          </div>
          <div className="homework-progress-bars">
            <div>
              <p>Completion</p>
              <div className="progress-meter">
                <span style={{ width: `${stats.completion}%` }} />
              </div>
            </div>
            <div>
              <p>Average score</p>
              <div className="progress-meter">
                <span style={{ width: `${stats.avgScore}%` }} />
              </div>
              <small>{stats.avgScore}%</small>
            </div>
          </div>
        </aside>
      </section>
    </section>
  );
}
