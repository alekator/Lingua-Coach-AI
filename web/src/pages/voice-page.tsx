import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { useAppStore } from "../store/app-store";

export function VoicePage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    const response = await api.voiceMessage({
      file,
      user_id: userId,
      target_lang: "en",
      language_hint: "en",
    });
    setResult(
      `Transcript: ${response.transcript}\nTeacher: ${response.teacher_text}\nAudio: ${response.audio_url}\nTip: ${response.pronunciation_feedback}`,
    );
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
      {result && <pre>{result}</pre>}
    </section>
  );
}
