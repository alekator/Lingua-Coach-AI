import { useQuery } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import type { VocabItem } from "../api/types";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

function sourceLabel(source: VocabItem["enrichment_source"]): string {
  switch ((source ?? "").toLowerCase()) {
    case "openai":
      return "OpenAI";
    case "local":
      return "Local";
    case "fallback":
      return "Fallback";
    case "manual":
      return "Manual";
    case "unknown":
      return "Manual";
    default:
      return "Manual";
  }
}

function sourceClass(source: VocabItem["enrichment_source"]): string {
  const normalized = (source ?? "").toLowerCase();
  if (normalized === "openai" || normalized === "local" || normalized === "fallback" || normalized === "manual") {
    return normalized;
  }
  return "manual";
}

export function VocabPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [word, setWord] = useState("achieve");
  const [translation, setTranslation] = useState("to achieve");
  const [reviewItem, setReviewItem] = useState<VocabItem | null>(null);
  const [reviewMsg, setReviewMsg] = useState("");
  const [actionError, setActionError] = useState("");
  const [isReviewLoading, setReviewLoading] = useState(false);
  const [isReviewSubmitting, setReviewSubmitting] = useState(false);
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
      setReviewItem(null);
      setActionError("");
      pushToast("success", "Word added with AI enrichment");
      await vocab.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    }
  }

  async function onReviewLoad() {
    setReviewLoading(true);
    try {
      const next = await api.vocabReviewNext({ user_id: userId });
      if (!next.has_item || !next.item) {
        setReviewItem(null);
        setReviewMsg("No due cards");
        pushToast("info", "No due cards");
        return;
      }
      setReviewItem(next.item);
      setReviewMsg("");
      setActionError("");
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    } finally {
      setReviewLoading(false);
    }
  }

  async function onReviewSubmit(rating: "again" | "hard" | "good" | "easy") {
    if (!reviewItem) return;
    setReviewSubmitting(true);
    try {
      const submit = await api.vocabReviewSubmit({
        user_id: userId,
        vocab_item_id: reviewItem.id,
        rating,
      });
      setReviewMsg(`Saved "${reviewItem.word}" as ${rating}. Next interval: ${submit.interval_days}d`);
      setReviewItem(null);
      setActionError("");
      pushToast("success", "Review submitted");
      await vocab.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    } finally {
      setReviewSubmitting(false);
    }
  }

  const totalItems = vocab.data?.items.length ?? 0;
  const withExample = useMemo(
    () => (vocab.data?.items ?? []).filter((item) => Boolean(item.example?.trim())).length,
    [vocab.data?.items],
  );
  const withPhonetics = useMemo(
    () => (vocab.data?.items ?? []).filter((item) => Boolean(item.phonetics?.trim())).length,
    [vocab.data?.items],
  );

  return (
    <section className="panel stack vocab-page">
      <header className="vocab-hero panel">
        <div>
          <h2>Word Bank + SRS</h2>
          <p>Add words, keep AI-enriched context, and review with spaced repetition.</p>
        </div>
      </header>
      <section className="vocab-grid">
        <article className="panel stack vocab-main-card">
          <form className="panel stack vocab-add-form" onSubmit={onAdd}>
            <h3>Add new word</h3>
            <label>
              Word
              <input value={word} onChange={(e) => setWord(e.target.value)} />
            </label>
            <label>
              Translation
              <input value={translation} onChange={(e) => setTranslation(e.target.value)} />
            </label>
            <button type="submit" className="cta-primary" disabled={!word.trim() || !translation.trim()}>
              Save to bank
            </button>
          </form>
          {actionError && <ErrorState text={actionError} />}
          {reviewMsg && <p className="vocab-review-msg">{reviewMsg}</p>}
          {vocab.isPending && <LoadingState text="Loading vocab..." />}
          {vocab.isError && <ErrorState text="Failed to load vocab list." />}
          {vocab.isSuccess && vocab.data.items.length === 0 && <EmptyState text="No vocab items yet." />}
          {vocab.isSuccess && vocab.data.items.length > 0 && (
            <div className="vocab-list">
              {vocab.data.items.map((item) => (
                <article key={item.id} className="vocab-item-card">
                  <p className="vocab-item-head">
                    <strong>{item.word}</strong>
                    <span>{item.translation}</span>
                  </p>
                  <div className="vocab-item-source-row">
                    <span
                      className={`badge vocab-source-badge ${sourceClass(item.enrichment_source)}`}
                      title={`Enrichment source: ${sourceLabel(item.enrichment_source)}`}
                    >
                      {sourceLabel(item.enrichment_source)}
                    </span>
                  </div>
                  {item.example && <p className="vocab-item-example">{item.example}</p>}
                  <p className="vocab-item-meta">
                    {item.phonetics ? `/${item.phonetics}/` : "phonetics: -"} | ease: {item.ease ?? "-"} | interval:{" "}
                    {item.interval_days ?? "-"}d
                  </p>
                </article>
              ))}
            </div>
          )}
        </article>
        <aside className="panel stack vocab-srs-card">
          <h3>Review Studio</h3>
          <article className="vocab-kpi-grid">
            <div>
              <p>Total words</p>
              <strong>{totalItems}</strong>
            </div>
            <div>
              <p>With examples</p>
              <strong>{withExample}</strong>
            </div>
            <div>
              <p>With phonetics</p>
              <strong>{withPhonetics}</strong>
            </div>
            <div>
              <p>Ready now</p>
              <strong>{reviewItem ? 1 : 0}</strong>
            </div>
          </article>
          <button type="button" className="cta-primary" onClick={onReviewLoad} disabled={isReviewLoading}>
            {isReviewLoading ? "Loading card..." : "Load next review card"}
          </button>
          {!reviewItem && !isReviewLoading && <EmptyState text="Load a due card and grade recall quality." />}
          {reviewItem && (
            <article className="panel stack vocab-review-card">
              <p className="vocab-review-word">{reviewItem.word}</p>
              <p className="vocab-review-translation">{reviewItem.translation}</p>
              {reviewItem.example && <p className="vocab-review-example">{reviewItem.example}</p>}
              <div className="vocab-review-actions">
                <button type="button" onClick={() => onReviewSubmit("again")} disabled={isReviewSubmitting}>
                  Again
                </button>
                <button type="button" onClick={() => onReviewSubmit("hard")} disabled={isReviewSubmitting}>
                  Hard
                </button>
                <button type="button" onClick={() => onReviewSubmit("good")} disabled={isReviewSubmitting}>
                  Good
                </button>
                <button type="button" onClick={() => onReviewSubmit("easy")} disabled={isReviewSubmitting}>
                  Easy
                </button>
              </div>
            </article>
          )}
        </aside>
      </section>
    </section>
  );
}
