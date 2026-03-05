import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function VoicePage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  const pushToast = useToastStore((s) => s.push);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    try {
      const response = await api.voiceMessage({
        file,
        user_id: userId,
        target_lang: "en",
        language_hint: "en",
      });
      const rubric = response.pronunciation_rubric;
      const rubricBlock = rubric
        ? `\nRubric: overall ${rubric.overall_score} (${rubric.level_band}), fluency ${rubric.fluency}, clarity ${rubric.clarity}\nTips: ${rubric.actionable_tips.join("; ")}`
        : "";
      setResult(
        `Transcript: ${response.transcript}\nTeacher: ${response.teacher_text}\nAudio: ${response.audio_url}\nTip: ${response.pronunciation_feedback}${rubricBlock}`,
      );
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
      <h2>Voice Conversation</h2>
      <form className="stack" onSubmit={onSubmit}>
        <label>
          Upload voice sample
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <button type="submit" disabled={!file}>
          Process voice
        </button>
      </form>
      {error && <ErrorState text={error} />}
      {result && <pre>{result}</pre>}
    </section>
  );
}
