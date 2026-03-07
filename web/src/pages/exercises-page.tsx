import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function ExercisesPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [searchParams] = useSearchParams();
  const queryTopic = (searchParams.get("topic") ?? "").trim().toLowerCase();
  const [topic, setTopic] = useState("travel");
  const autoStartedRef = useRef(false);
  const [items, setItems] = useState<
    Array<{ id: string; prompt: string; expected_answer: string; type: string }>
  >([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [score, setScore] = useState<string>("");
  const [rubricRows, setRubricRows] = useState<Array<{ id: string; itemScore: number; feedback: string }>>([]);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [grading, setGrading] = useState(false);
  const pushToast = useToastStore((s) => s.push);
  const errorBank = useQuery({
    queryKey: ["coach-error-bank", userId],
    queryFn: () => api.coachErrorBank(userId, 3),
  });

  useEffect(() => {
    if (!queryTopic) return;
    if (autoStartedRef.current) return;
    autoStartedRef.current = true;
    setTopic(queryTopic);
    void generateDrillSet(queryTopic);
  }, [queryTopic]);

  async function generateDrillSet(topicValue: string) {
    setGenerating(true);
    try {
      const response = await api.generateExercises({
        user_id: userId,
        exercise_type: "fill_blank",
        topic: topicValue,
        count: 3,
      });
      setItems(response.items);
      setAnswers({});
      setScore("");
      setRubricRows([]);
      setError("");
      pushToast("success", `Exercises generated for ${topicValue}`);
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setGenerating(false);
    }
  }

  async function onGenerate(event: FormEvent) {
    event.preventDefault();
    await generateDrillSet(topic);
  }

  async function onGrade(event: FormEvent) {
    event.preventDefault();
    const expected = Object.fromEntries(items.map((item) => [item.id, item.expected_answer]));
    setGrading(true);
    try {
      const response = await api.gradeExercises({ answers, expected });
      setScore(`${response.score}/${response.max_score}`);
      const rows = Object.entries(response.rubric ?? {}).map(([itemId, row]) => ({
        id: itemId,
        itemScore: Number(row.item_score ?? 0),
        feedback: String(row.feedback ?? ""),
      }));
      setRubricRows(rows);
      setError("");
      pushToast("info", `Scored ${response.score}/${response.max_score}`);
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setGrading(false);
    }
  }

  const hasItems = useMemo(() => items.length > 0, [items]);
  const answeredCount = useMemo(
    () => items.filter((item) => (answers[item.id] ?? "").trim().length > 0).length,
    [answers, items],
  );
  const completionPercent = hasItems ? Math.round((answeredCount / items.length) * 100) : 0;
  const scoreParts = score.includes("/") ? score.split("/") : [];
  const scorePercent = scoreParts.length === 2 ? Math.round((Number(scoreParts[0]) / Number(scoreParts[1] || 1)) * 100) : 0;
  const rubricQualityPercent = rubricRows.length
    ? Math.round((rubricRows.reduce((acc, row) => acc + row.itemScore, 0) / rubricRows.length) * 100)
    : scorePercent;

  return (
    <section className="panel stack drills-page">
      <header className="drills-hero panel">
        <div>
          <h2>Targeted Drills</h2>
          <p>Generate a compact drill set, answer each prompt, and get rubric-backed feedback.</p>
        </div>
      </header>
      <section className="drills-grid">
        <article className="panel stack drills-main-card">
          {errorBank.isPending && <LoadingState text="Loading recurring errors..." />}
          {errorBank.isSuccess && errorBank.data.items.length > 0 && (
            <article className="panel stack drills-error-focus">
              <h3>Recurring Error Focus</h3>
              {errorBank.data.items.map((item) => (
                <div key={`${item.category}-${item.latest_bad}`} className="drills-focus-row">
                  <p>
                    {item.category} ({item.occurrences}x): {item.latest_bad} {"->"} {item.latest_good}
                  </p>
                  <button
                    type="button"
                    onClick={async () => {
                      setTopic(item.category);
                      await generateDrillSet(item.category);
                    }}
                  >
                    Use this drill
                  </button>
                </div>
              ))}
            </article>
          )}
          <form onSubmit={onGenerate} className="panel stack drills-generate-card">
            <h3>Step 1: Generate drill set</h3>
            <label>
              Topic
              <input value={topic} onChange={(e) => setTopic(e.target.value)} />
            </label>
            <button type="submit" className="cta-primary" disabled={generating || !topic.trim()}>
              {generating ? "Generating..." : "Generate drill set"}
            </button>
          </form>
          {error && <ErrorState text={error} />}
          {!hasItems && !generating && <EmptyState text="Generate a set to start practice." />}
          {hasItems && (
            <form className="panel stack drills-answer-card" onSubmit={onGrade}>
              <h3>Step 2: Answer prompts</h3>
              {items.map((item, idx) => (
                <label key={item.id} className="drills-item-row">
                  <span>
                    {idx + 1}. {item.prompt}
                  </span>
                  <input
                    value={answers[item.id] ?? ""}
                    onChange={(e) => setAnswers((prev) => ({ ...prev, [item.id]: e.target.value }))}
                  />
                </label>
              ))}
              <button type="submit" className="cta-primary" disabled={grading || answeredCount === 0}>
                {grading ? "Grading..." : "Grade with coach rubric"}
              </button>
            </form>
          )}
          {score && <p className="drills-score-line">Score: {score}</p>}
          {rubricRows.length > 0 && (
            <article className="panel stack drills-rubric-card">
              <h3>Coach Rubric Notes</h3>
              {rubricRows.map((row) => (
                <p key={row.id}>
                  {row.id}: {row.itemScore.toFixed(2)} ({row.feedback})
                </p>
              ))}
            </article>
          )}
        </article>
        <aside className="panel stack drills-progress-card">
          <h3>Drill Progress</h3>
          <article className="drills-kpi-grid">
            <div>
              <p>Items</p>
              <strong>{items.length}</strong>
            </div>
            <div>
              <p>Answered</p>
              <strong>{answeredCount}</strong>
            </div>
            <div>
              <p>Completion</p>
              <strong>{completionPercent}%</strong>
            </div>
            <div>
              <p>Last score</p>
              <strong>{score ? `${scorePercent}%` : "n/a"}</strong>
            </div>
          </article>
          <article className="drills-meter-card">
            <p>Completion</p>
            <div className="progress-meter" role="img" aria-label="Drill completion">
              <span style={{ width: `${completionPercent}%` }} />
            </div>
          </article>
          <article className="drills-meter-card">
            <p>Score quality</p>
            <div className="progress-meter" role="img" aria-label="Drill score quality">
              <span style={{ width: `${rubricQualityPercent}%` }} />
            </div>
          </article>
        </aside>
      </section>
    </section>
  );
}
