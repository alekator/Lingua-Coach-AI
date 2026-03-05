import { FormEvent, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAppStore } from "../store/app-store";

export function ExercisesPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [items, setItems] = useState<
    Array<{ id: string; prompt: string; expected_answer: string; type: string }>
  >([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [score, setScore] = useState<string>("");

  async function onGenerate(event: FormEvent) {
    event.preventDefault();
    const response = await api.generateExercises({
      user_id: userId,
      exercise_type: "fill_blank",
      topic: "travel",
      count: 3,
    });
    setItems(response.items);
    setAnswers({});
    setScore("");
  }

  async function onGrade(event: FormEvent) {
    event.preventDefault();
    const expected = Object.fromEntries(items.map((item) => [item.id, item.expected_answer]));
    const response = await api.gradeExercises({ answers, expected });
    setScore(`${response.score}/${response.max_score}`);
  }

  const hasItems = useMemo(() => items.length > 0, [items]);

  return (
    <section className="panel stack">
      <h2>Exercises</h2>
      <form onSubmit={onGenerate}>
        <button type="submit">Generate set</button>
      </form>
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
