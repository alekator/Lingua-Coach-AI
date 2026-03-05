import { FormEvent, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { EmptyState, ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function ExercisesPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [topic, setTopic] = useState("travel");
  const [items, setItems] = useState<
    Array<{ id: string; prompt: string; expected_answer: string; type: string }>
  >([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [score, setScore] = useState<string>("");
  const [rubricRows, setRubricRows] = useState<string[]>([]);
  const [error, setError] = useState("");
  const pushToast = useToastStore((s) => s.push);
  const errorBank = useQuery({
    queryKey: ["coach-error-bank", userId],
    queryFn: () => api.coachErrorBank(userId, 3),
  });

  async function generateDrillSet(topicValue: string) {
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
    }
  }

  async function onGenerate(event: FormEvent) {
    event.preventDefault();
    await generateDrillSet(topic);
  }

  async function onGrade(event: FormEvent) {
    event.preventDefault();
    const expected = Object.fromEntries(items.map((item) => [item.id, item.expected_answer]));
    try {
      const response = await api.gradeExercises({ answers, expected });
      setScore(`${response.score}/${response.max_score}`);
      const rows = Object.entries(response.rubric ?? {}).map(
        ([itemId, row]) => `${itemId}: ${row.item_score} (${row.feedback})`,
      );
      setRubricRows(rows);
      setError("");
      pushToast("info", `Scored ${response.score}/${response.max_score}`);
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    }
  }

  const hasItems = useMemo(() => items.length > 0, [items]);

  return (
    <section className="panel stack">
      <h2>Targeted Drills</h2>
      <p>Generate a compact drill set, then grade with rubric-backed feedback.</p>
      {errorBank.isSuccess && errorBank.data.items.length > 0 && (
        <article className="panel stack">
          <h3>Recurring Error Focus</h3>
          {errorBank.data.items.map((item) => (
            <div key={`${item.category}-${item.latest_bad}`} className="row">
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
      <form onSubmit={onGenerate}>
        <label>
          Topic
          <input value={topic} onChange={(e) => setTopic(e.target.value)} />
        </label>
        <button type="submit">Generate drill set</button>
      </form>
      {error && <ErrorState text={error} />}
      {!hasItems && <EmptyState text="Generate a set to start practice." />}
      {hasItems && (
        <form className="stack" onSubmit={onGrade}>
          {items.map((item) => (
            <label key={item.id}>
              {item.prompt}
              <input
                value={answers[item.id] ?? ""}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [item.id]: e.target.value }))}
              />
            </label>
          ))}
          <button type="submit">Grade with coach rubric</button>
        </form>
      )}
      {score && <p>Score: {score}</p>}
      {rubricRows.length > 0 && (
        <article className="panel">
          <h3>Coach Rubric Notes</h3>
          {rubricRows.map((row) => (
            <p key={row}>- {row}</p>
          ))}
        </article>
      )}
    </section>
  );
}
