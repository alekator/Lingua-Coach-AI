import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import type { VoiceMessageResponse } from "../api/types";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

function extractCoachTarget(text: string): string {
  const marker = "You should say:";
  const index = text.indexOf(marker);
  if (index < 0) return "";
  return text.slice(index + marker.length).trim().replace(/\.$/, "");
}

export function VoicePage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const targetLang = useAppStore((s) => s.activeWorkspaceTargetLang) ?? "en";
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<VoiceMessageResponse | null>(null);
  const [error, setError] = useState("");
  const [practicePhrase, setPracticePhrase] = useState("");
  const [coachTarget, setCoachTarget] = useState("");
  const pushToast = useToastStore((s) => s.push);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    try {
      const response = await api.voiceMessage({
        file,
        user_id: userId,
        target_lang: targetLang,
        language_hint: targetLang,
      });
      setResult(response);
      setCoachTarget(extractCoachTarget(response.teacher_text));
      setError("");
      pushToast("success", "Voice message processed");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    }
  }

  return (
    <section className="panel stack">
      <h2>Coach Voice Practice</h2>
      <p>Practice language: {targetLang.toUpperCase()}</p>
      <p>Upload one short response, review feedback, then retry with one clear improvement.</p>
      <label>
        Practice phrase (optional retry line)
        <input
          placeholder="Example: I went to school yesterday."
          value={practicePhrase}
          onChange={(e) => setPracticePhrase(e.target.value)}
        />
      </label>
      {practicePhrase && <p>Retry plan: say this phrase clearly in your next recording.</p>}
      <form className="stack" onSubmit={onSubmit}>
        <label>
          Upload voice sample (10-45 sec)
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <button type="submit" disabled={!file}>
          Analyze voice
        </button>
      </form>
      {error && <ErrorState text={error} />}
      {result && (
        <article className="panel stack">
          <h3>Coach feedback</h3>
          <p>Transcript: {result.transcript}</p>
          <p>Coach: {result.teacher_text}</p>
          <p>Pronunciation tip: {result.pronunciation_feedback}</p>
          {result.pronunciation_rubric && (
            <>
              <p>
                Rubric: {result.pronunciation_rubric.overall_score} ({result.pronunciation_rubric.level_band})
              </p>
              <p>
                Fluency {result.pronunciation_rubric.fluency} | Clarity {result.pronunciation_rubric.clarity} |
                Grammar {result.pronunciation_rubric.grammar_accuracy}
              </p>
              {result.pronunciation_rubric.actionable_tips.map((tip, idx) => (
                <p key={`voice-tip-${idx}`}>- {tip}</p>
              ))}
            </>
          )}
          <p>Coach audio reply: {result.audio_url}</p>
          {coachTarget && (
            <button
              type="button"
              onClick={() => {
                setPracticePhrase(coachTarget);
                pushToast("info", "Coach target applied for retry");
              }}
            >
              Use coach target for retry
            </button>
          )}
        </article>
      )}
    </section>
  );
}
