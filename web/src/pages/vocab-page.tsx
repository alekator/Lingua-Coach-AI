import { useQuery } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function VocabPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [word, setWord] = useState("achieve");
  const [translation, setTranslation] = useState("to achieve");
  const [reviewMsg, setReviewMsg] = useState("");
  const [actionError, setActionError] = useState("");
  const pushToast = useToastStore((s) => s.push);
  const vocab = useQuery({
    queryKey: ["vocab", userId, reviewMsg],
    queryFn: () => api.vocabList(userId),
  });

  async function onAdd(event: FormEvent) {
    event.preventDefault();
    try {
      await api.vocabAdd({ user_id: userId, word, translation });
      setWord("");
      setTranslation("");
      setActionError("");
      pushToast("success", "Word added");
      await vocab.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    }
  }

  async function onReview() {
    try {
      const next = await api.vocabReviewNext({ user_id: userId });
      if (!next.has_item || !next.item) {
        setReviewMsg("No due cards");
        pushToast("info", "No due cards");
        return;
      }
      const submit = await api.vocabReviewSubmit({
        user_id: userId,
        vocab_item_id: next.item.id,
        rating: "good",
      });
      setReviewMsg(`Reviewed item ${submit.vocab_item_id}, next interval ${submit.interval_days}d`);
      setActionError("");
      pushToast("success", "Review submitted");
      await vocab.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    }
  }

  return (
    <section className="panel stack">
      <h2>Vocab + SRS</h2>
      <form className="stack" onSubmit={onAdd}>
        <label>
          Word
          <input value={word} onChange={(e) => setWord(e.target.value)} />
        </label>
        <label>
          Translation
          <input value={translation} onChange={(e) => setTranslation(e.target.value)} />
        </label>
        <button type="submit">Add word</button>
      </form>
      <button type="button" onClick={onReview}>
        Review next (good)
      </button>
      {actionError && <ErrorState text={actionError} />}
      {reviewMsg && <p>{reviewMsg}</p>}
      {vocab.isPending && <LoadingState text="Loading vocab..." />}
      {vocab.isError && <ErrorState text="Failed to load vocab list." />}
      {vocab.isSuccess && vocab.data.items.length === 0 && <EmptyState text="No vocab items yet." />}
      {vocab.isSuccess && (
        <div className="stack">
          {vocab.data.items.map((item) => (
            <article key={item.id} className="panel">
              <strong>{item.word}</strong> - {item.translation}
              <p>
                ease: {item.ease ?? "-"} | interval: {item.interval_days ?? "-"}
              </p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
