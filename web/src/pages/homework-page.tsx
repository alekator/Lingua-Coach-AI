import { useQuery } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function HomeworkPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [title, setTitle] = useState("Daily grammar drill");
  const [submitMsg, setSubmitMsg] = useState("");
  const [actionError, setActionError] = useState("");
  const pushToast = useToastStore((s) => s.push);
  const list = useQuery({
    queryKey: ["homework", userId, submitMsg],
    queryFn: () => api.homeworkList(userId),
  });

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    try {
      await api.homeworkCreate({
        user_id: userId,
        title,
        tasks: [
          { id: "t1", type: "rewrite", prompt: "Fix the sentence: I goed there." },
          { id: "t2", type: "translate", prompt: "Translate: I have finished my work." },
        ],
      });
      setTitle("");
      setActionError("");
      pushToast("success", "Homework created");
      await list.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    }
  }

  async function onSubmit(homeworkId: number) {
    try {
      const response = await api.homeworkSubmit({
        homework_id: homeworkId,
        answers: { t1: "I went there.", t2: "He terminado mi trabajo." },
      });
      setSubmitMsg(`Homework ${response.homework_id} submitted, score ${response.grade.score}`);
      setActionError("");
      pushToast("success", "Homework submitted");
      await list.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    }
  }

  return (
    <section className="panel stack">
      <h2>Coach Homework</h2>
      <p>Assign focused tasks and submit sample answers to get structured grading.</p>
      <form onSubmit={onCreate} className="stack">
        <label>
          Homework title
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <button type="submit">Create homework</button>
      </form>
      {actionError && <ErrorState text={actionError} />}
      {submitMsg && <p>{submitMsg}</p>}
      {list.isPending && <LoadingState text="Loading homework..." />}
      {list.isError && <ErrorState text="Failed to load homework." />}
      {list.isSuccess && list.data.items.length === 0 && <EmptyState text="No homework yet." />}
      {list.isSuccess && (
        <div className="stack">
          {list.data.items.map((item) => (
            <article key={item.id} className="panel">
              <h3>{item.title}</h3>
              <p>Status: {item.status}</p>
              <button type="button" onClick={() => onSubmit(item.id)} disabled={item.status === "submitted"}>
                Submit to coach
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
