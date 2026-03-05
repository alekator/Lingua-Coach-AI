import { useQuery } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { useAppStore } from "../store/app-store";

export function HomeworkPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [title, setTitle] = useState("Daily grammar drill");
  const [submitMsg, setSubmitMsg] = useState("");
  const list = useQuery({
    queryKey: ["homework", userId, submitMsg],
    queryFn: () => api.homeworkList(userId),
  });

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    await api.homeworkCreate({
      user_id: userId,
      title,
      tasks: [
        { id: "t1", type: "rewrite", prompt: "Fix the sentence: I goed there." },
        { id: "t2", type: "translate", prompt: "Translate: I have finished my work." },
      ],
    });
    setTitle("");
    await list.refetch();
  }

  async function onSubmit(homeworkId: number) {
    const response = await api.homeworkSubmit({
      homework_id: homeworkId,
      answers: { t1: "I went there.", t2: "He terminado mi trabajo." },
    });
    setSubmitMsg(`Homework ${response.homework_id} submitted, score ${response.grade.score}`);
    await list.refetch();
  }

  return (
    <section className="panel stack">
      <h2>Homework</h2>
      <form onSubmit={onCreate} className="stack">
        <label>
          Homework title
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <button type="submit">Create homework</button>
      </form>
      {submitMsg && <p>{submitMsg}</p>}
      {list.isSuccess && (
        <div className="stack">
          {list.data.items.map((item) => (
            <article key={item.id} className="panel">
              <h3>{item.title}</h3>
              <p>Status: {item.status}</p>
              <button type="button" onClick={() => onSubmit(item.id)} disabled={item.status === "submitted"}>
                Submit sample answers
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
