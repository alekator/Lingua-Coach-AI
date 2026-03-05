import { useQuery } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { useAppStore } from "../store/app-store";

export function VocabPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [word, setWord] = useState("achieve");
  const [translation, setTranslation] = useState("to achieve");
  const [reviewMsg, setReviewMsg] = useState("");
  const vocab = useQuery({
    queryKey: ["vocab", userId, reviewMsg],
    queryFn: () => api.vocabList(userId),
  });

  async function onAdd(event: FormEvent) {
    event.preventDefault();
    await api.vocabAdd({ user_id: userId, word, translation });
    setWord("");
    setTranslation("");
    await vocab.refetch();
  }

  async function onReview() {
    const next = await api.vocabReviewNext({ user_id: userId });
    if (!next.has_item || !next.item) {
      setReviewMsg("No due cards");
      return;
    }
    const submit = await api.vocabReviewSubmit({
      user_id: userId,
      vocab_item_id: next.item.id,
      rating: "good",
    });
    setReviewMsg(`Reviewed item ${submit.vocab_item_id}, next interval ${submit.interval_days}d`);
    await vocab.refetch();
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
      {reviewMsg && <p>{reviewMsg}</p>}
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
