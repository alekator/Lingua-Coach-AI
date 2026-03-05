import { FormEvent, useState } from "react";
import { api } from "../api/client";
import type { GrammarAnalyzeResponse } from "../api/types";

export function GrammarPage() {
  const [text, setText] = useState("I goed to school");
  const [result, setResult] = useState<GrammarAnalyzeResponse | null>(null);

  async function onAnalyze(event: FormEvent) {
    event.preventDefault();
    const response = await api.grammarAnalyze({ text, target_lang: "en" });
    setResult(response);
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
