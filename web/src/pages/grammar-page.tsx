import { useQuery } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import type { GrammarAnalyzeResponse } from "../api/types";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function GrammarPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const targetLang = useAppStore((s) => s.activeWorkspaceTargetLang) ?? "en";
  const [text, setText] = useState("I goed to school");
  const [result, setResult] = useState<GrammarAnalyzeResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pushToast = useToastStore((s) => s.push);
  const history = useQuery({
    queryKey: ["grammar-history", userId],
    queryFn: () => api.grammarHistory(userId, 40),
  });

  async function onAnalyze(event: FormEvent) {
    event.preventDefault();
    const cleanText = text.trim();
    if (!cleanText) {
      setError("Enter text to analyze.");
      return;
    }
    setBusy(true);
    try {
      const response = await api.grammarAnalyze({ user_id: userId, text: cleanText, target_lang: targetLang });
      setResult(response);
      setError("");
      pushToast("success", "Grammar analysis completed");
      void history.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel stack grammar-page">
      <header className="grammar-hero panel">
        <div>
          <h2>Grammar Analyzer</h2>
          <p>AI-powered correction for your target language: {targetLang.toUpperCase()}.</p>
        </div>
      </header>
      <section className="grammar-grid">
        <article className="panel stack grammar-analyzer-card">
          <form onSubmit={onAnalyze} className="stack grammar-analyzer-form">
            <label>
              Text
              <textarea value={text} onChange={(e) => setText(e.target.value)} rows={10} />
            </label>
            <button type="submit" className="cta-primary" disabled={busy || !text.trim()}>
              {busy ? "Analyzing..." : "Analyze"}
            </button>
          </form>
          {error && <ErrorState text={error} />}
          {!result && !error && <EmptyState text="Run analysis to get corrected text, mistakes, and exercises." />}
          {result && (
            <div className="stack grammar-result-card">
              <article className="panel">
                <h3>Corrected Answer</h3>
                <p>{result.corrected_text}</p>
              </article>
              {result.errors.length > 0 && (
                <article className="panel stack">
                  <h3>Mistakes Found</h3>
                  {result.errors.map((item, idx) => (
                    <div key={`${item.category}-${idx}`} className="grammar-error-row">
                      <span className="badge">{item.category}</span>
                      <p>
                        {item.bad} {"->"} {item.good}
                      </p>
                      <small>{item.explanation}</small>
                    </div>
                  ))}
                </article>
              )}
              {result.exercises.length > 0 && (
                <article className="panel stack">
                  <h3>Follow-up Practice</h3>
                  {result.exercises.map((exercise) => (
                    <p key={exercise} className="grammar-exercise-line">
                      {exercise}
                    </p>
                  ))}
                </article>
              )}
            </div>
          )}
        </article>
        <aside className="panel stack grammar-history-card" aria-live="polite">
          <div className="grammar-history-head">
            <h3>Answer Memory</h3>
            <span className="badge">{history.data?.items.length ?? 0} saved</span>
          </div>
          {history.isPending && <LoadingState text="Loading saved answers..." />}
          {history.isError && <ErrorState text="Failed to load grammar history." />}
          {history.isSuccess && history.data.items.length === 0 && (
            <EmptyState text="Your analyzed answers will appear here." />
          )}
          {history.isSuccess && history.data.items.length > 0 && (
            <div className="grammar-history-list">
              {history.data.items.map((item) => (
                <article key={item.id} className="grammar-history-item">
                  <p className="grammar-history-time">
                    {new Date(item.created_at).toLocaleString()} | {item.target_lang.toUpperCase()}
                  </p>
                  <p className="grammar-history-original">{item.input_text}</p>
                  <p className="grammar-history-corrected">{item.corrected_text}</p>
                </article>
              ))}
            </div>
          )}
        </aside>
      </section>
    </section>
  );
}
