import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import type { GrammarAnalyzeResponse } from "../api/types";
import { useToastStore } from "../store/toast-store";

export function GrammarPage() {
  const [text, setText] = useState("I goed to school");
  const [result, setResult] = useState<GrammarAnalyzeResponse | null>(null);
  const [error, setError] = useState("");
  const pushToast = useToastStore((s) => s.push);

  async function onAnalyze(event: FormEvent) {
    event.preventDefault();
    try {
      const response = await api.grammarAnalyze({ text, target_lang: "en" });
      setResult(response);
      setError("");
      pushToast("success", "Grammar analysis completed");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    }
  }

  return (
    <section className="panel stack">
      <h2>Grammar Analyzer</h2>
      <form onSubmit={onAnalyze} className="stack">
        <label>
          Text
          <input value={text} onChange={(e) => setText(e.target.value)} />
        </label>
        <button type="submit">Analyze</button>
      </form>
      {error && <ErrorState text={error} />}
      {!result && <EmptyState text="Enter text and run analysis to get corrections." />}
      {result && (
        <>
          <p>Corrected: {result.corrected_text}</p>
          {result.errors.map((error, idx) => (
            <article key={`${error.category}-${idx}`} className="panel">
              <strong>{error.category}</strong>
              <p>
                {error.bad} {"->"} {error.good}
              </p>
              <p>{error.explanation}</p>
            </article>
          ))}
        </>
      )}
    </section>
  );
}
