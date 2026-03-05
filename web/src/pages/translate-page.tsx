import { FormEvent, useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useToastStore } from "../store/toast-store";

export function TranslatePage() {
  const [text, setText] = useState("Hello world");
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("es");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<string>("");
  const [voiceResult, setVoiceResult] = useState<string>("");
  const [error, setError] = useState("");
  const pushToast = useToastStore((s) => s.push);

  async function onTranslate(event: FormEvent) {
    event.preventDefault();
    try {
      const response = await api.translate({
        text,
        source_lang: sourceLang,
        target_lang: targetLang,
        voice: true,
      });
      setResult(`${response.translated_text}${response.audio_url ? ` | ${response.audio_url}` : ""}`);
      setError("");
      pushToast("success", "Text translated");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    }
  }

  async function onTranslateVoice(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    try {
      const response = await api.translateVoice({
        file,
        source_lang: sourceLang,
        target_lang: targetLang,
        language_hint: sourceLang,
      });
      setVoiceResult(`${response.transcript} -> ${response.translated_text} | ${response.audio_url}`);
      setError("");
      pushToast("success", "Voice translated");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    }
  }

  return (
    <section className="panel stack">
      <h2>Translate</h2>
      <form className="stack" onSubmit={onTranslate}>
        <label>
          Source
          <input value={sourceLang} onChange={(e) => setSourceLang(e.target.value)} />
        </label>
        <label>
          Target
          <input value={targetLang} onChange={(e) => setTargetLang(e.target.value)} />
        </label>
        <label>
          Text
          <input value={text} onChange={(e) => setText(e.target.value)} />
        </label>
        <button type="submit">Translate text</button>
      </form>
      {error && <ErrorState text={error} />}
      {result && <p>{result}</p>}

      <form className="stack" onSubmit={onTranslateVoice}>
        <label>
          Voice input
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <button type="submit" disabled={!file}>
          Translate voice
        </button>
      </form>
      {voiceResult && <p>{voiceResult}</p>}
    </section>
  );
}
