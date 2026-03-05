import { FormEvent, useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function ExercisesPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [items, setItems] = useState<
    Array<{ id: string; prompt: string; expected_answer: string; type: string }>
  >([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [score, setScore] = useState<string>("");
  const [error, setError] = useState("");
  const pushToast = useToastStore((s) => s.push);

  async function onGenerate(event: FormEvent) {
    event.preventDefault();
    try {
      const response = await api.generateExercises({
        user_id: userId,
        exercise_type: "fill_blank",
        topic: "travel",
        count: 3,
      });
      setItems(response.items);
      setAnswers({});
      setScore("");
      setError("");
      pushToast("success", "Exercises generated");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    }
  }

  async function onGrade(event: FormEvent) {
    event.preventDefault();
    const expected = Object.fromEntries(items.map((item) => [item.id, item.expected_answer]));
    try {
      const response = await api.gradeExercises({ answers, expected });
      setScore(`${response.score}/${response.max_score}`);
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
      <h2>Exercises</h2>
      <form onSubmit={onGenerate}>
        <button type="submit">Generate set</button>
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
          <button type="submit">Grade answers</button>
        </form>
      )}
      {score && <p>Score: {score}</p>}
    </section>
  );
}
