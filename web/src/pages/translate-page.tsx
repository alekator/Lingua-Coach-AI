import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";
import { FilePicker } from "../components/file-picker";
import { AudioRecorder } from "../components/audio-recorder";
import { AudioPlayer } from "../components/audio-player";

type TranslateHistoryItem = {
  id: string;
  kind: "text" | "voice";
  sourceLang: string;
  targetLang: string;
  inputText: string;
  outputText: string;
  engine: string;
  createdAt: string;
};

export function TranslatePage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const nativeLang = useAppStore((s) => s.activeWorkspaceNativeLang);
  const workspaceTargetLang = useAppStore((s) => s.activeWorkspaceTargetLang);
  const [text, setText] = useState("Hello world");
  const [sourceLang, setSourceLang] = useState(nativeLang ?? "en");
  const [targetLang, setTargetLang] = useState(workspaceTargetLang ?? "es");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<string>("");
  const [engineUsed, setEngineUsed] = useState<"openai" | "local" | "fallback" | "unknown">("unknown");
  const [voiceResult, setVoiceResult] = useState<string>("");
  const [voiceEngineUsed, setVoiceEngineUsed] = useState<"openai" | "local" | "fallback" | "unknown">("unknown");
  const [history, setHistory] = useState<TranslateHistoryItem[]>([]);
  const [textAudioUrl, setTextAudioUrl] = useState<string | null>(null);
  const [voiceAudioUrl, setVoiceAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busyText, setBusyText] = useState(false);
  const [busyVoice, setBusyVoice] = useState(false);
  const pushToast = useToastStore((s) => s.push);
  const historyStorageKey = `translate-memory:v2:user:${userId}`;

  const quickPrompts = [
    "How long does it take to get to the airport?",
    "Can I reschedule our meeting to tomorrow morning?",
    "I need help understanding this invoice.",
    "Please speak slower, I am still learning.",
  ];

  useEffect(() => {
    if (nativeLang) {
      setSourceLang(nativeLang);
    }
    if (workspaceTargetLang) {
      setTargetLang(workspaceTargetLang);
    }
  }, [nativeLang, workspaceTargetLang]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(historyStorageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw) as TranslateHistoryItem[];
      if (!Array.isArray(parsed)) return;
      setHistory(
        parsed.filter((item) => item && typeof item.id === "string" && typeof item.outputText === "string").slice(0, 12),
      );
    } catch {
      // ignore malformed storage
    }
  }, [historyStorageKey]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(historyStorageKey, JSON.stringify(history.slice(0, 12)));
    } catch {
      // storage quota or privacy mode
    }
  }, [history, historyStorageKey]);

  function pushHistory(item: TranslateHistoryItem) {
    setHistory((prev) => [item, ...prev].slice(0, 12));
  }

  function resolveEngineLabel(engine: string) {
    switch (engine.toLowerCase()) {
      case "openai":
        return "OpenAI";
      case "local":
        return "Local";
      case "fallback":
        return "Fallback";
      default:
        return "Unknown";
    }
  }

  function resolveEngineClass(engine: string) {
    const value = engine.toLowerCase();
    if (value === "openai" || value === "local" || value === "fallback") return value;
    return "fallback";
  }

  function shouldShowEngineBadge(engine: string) {
    const value = engine.trim().toLowerCase();
    return value === "openai" || value === "local" || value === "fallback";
  }

  function swapLanguages() {
    setSourceLang(targetLang);
    setTargetLang(sourceLang);
  }

  async function copyResult() {
    if (!result.trim()) return;
    try {
      await navigator.clipboard.writeText(result);
      pushToast("success", "Translation copied");
    } catch {
      pushToast("error", "Failed to copy translation");
    }
  }

  async function onTranslate(event: FormEvent) {
    event.preventDefault();
    setBusyText(true);
    try {
      const response = await api.translate({
        user_id: userId,
        text,
        source_lang: sourceLang,
        target_lang: targetLang,
        voice: true,
      });
      setResult(response.translated_text);
      setTextAudioUrl(response.audio_url ?? null);
      setEngineUsed((response.engine_used ?? "unknown") as "openai" | "local" | "fallback" | "unknown");
      pushHistory({
        id: `txt-${Date.now()}`,
        kind: "text",
        sourceLang,
        targetLang,
        inputText: text,
        outputText: response.translated_text,
        engine: response.engine_used ?? "unknown",
        createdAt: new Date().toISOString(),
      });
      setError("");
      pushToast("success", "Text translated");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setBusyText(false);
    }
  }

  async function onTranslateVoice(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusyVoice(true);
    try {
      const response = await api.translateVoice({
        file,
        source_lang: sourceLang,
        target_lang: targetLang,
        language_hint: sourceLang,
      });
      setVoiceResult(`${response.transcript} -> ${response.translated_text}`);
      setVoiceEngineUsed((response.engine_used ?? "unknown") as "openai" | "local" | "fallback" | "unknown");
      setVoiceAudioUrl(response.audio_url ?? null);
      pushHistory({
        id: `voice-${Date.now()}`,
        kind: "voice",
        sourceLang,
        targetLang,
        inputText: response.transcript,
        outputText: response.translated_text,
        engine: response.engine_used ?? "unknown",
        createdAt: new Date().toISOString(),
      });
      setError("");
      pushToast("success", "Voice translated");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setBusyVoice(false);
    }
  }

  return (
    <section className="panel stack translate-page">
      <header className="translate-hero panel">
        <div>
          <h2>Translator Lab</h2>
          <p>
            Smart pair from active space: {(nativeLang ?? sourceLang).toUpperCase()} {"->"}{" "}
            {(workspaceTargetLang ?? targetLang).toUpperCase()}
          </p>
        </div>
        <div className="translate-quick-prompts">
          {quickPrompts.map((prompt) => (
            <button key={prompt} type="button" className="translate-prompt-chip" onClick={() => setText(prompt)}>
              {prompt}
            </button>
          ))}
        </div>
      </header>

      <section className="translate-grid">
        <article className="panel stack translate-main-card">
          <form className="panel stack translate-form" onSubmit={onTranslate}>
            <div className="translate-pair-row">
              <label>
                Source
                <input value={sourceLang} onChange={(e) => setSourceLang(e.target.value)} />
              </label>
              <button type="button" className="translate-swap-btn" onClick={swapLanguages} aria-label="Swap languages">
                ⇄
              </button>
              <label>
                Target
                <input value={targetLang} onChange={(e) => setTargetLang(e.target.value)} />
              </label>
            </div>
            <label>
              Text
              <textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} />
            </label>
            <button type="submit" className="cta-primary" disabled={!text.trim() || busyText}>
              {busyText ? "Translating..." : "Translate text"}
            </button>
          </form>

          {error && <ErrorState text={error} />}

          <article className="panel stack translate-output-card">
            <div className="translate-output-head">
              <h3>Result</h3>
              {shouldShowEngineBadge(engineUsed) && (
                <span className={`badge translate-engine-badge ${resolveEngineClass(engineUsed)}`}>
                  {resolveEngineLabel(engineUsed)}
                </span>
              )}
            </div>
            <p className="translate-result-text">{result || "Your translated text will appear here."}</p>
            <div className="row">
              <button type="button" onClick={copyResult} disabled={!result.trim()}>
                Copy
              </button>
            </div>
            <AudioPlayer audioUrl={textAudioUrl} label="Text translation audio" />
          </article>

          <form className="panel stack translate-voice-form" onSubmit={onTranslateVoice}>
            <h3>Voice Translator</h3>
            <label>
              Voice input
              <FilePicker id="translate-voice-file" ariaLabel="Voice input" accept="audio/*" onFileChange={setFile} />
            </label>
            <label>
              Or record with microphone
              <AudioRecorder onRecordedFile={setFile} />
            </label>
            <button type="submit" className="cta-primary" disabled={!file || busyVoice}>
              {busyVoice ? "Translating voice..." : "Translate voice"}
            </button>
            {voiceResult && (
              <article className="translate-voice-result">
                <div className="translate-output-head">
                  <strong>Voice result</strong>
                  {shouldShowEngineBadge(voiceEngineUsed) && (
                    <span className={`badge translate-engine-badge ${resolveEngineClass(voiceEngineUsed)}`}>
                      {resolveEngineLabel(voiceEngineUsed)}
                    </span>
                  )}
                </div>
                <p>{voiceResult}</p>
                <AudioPlayer audioUrl={voiceAudioUrl} label="Voice translation audio" />
              </article>
            )}
          </form>
        </article>

        <aside className="panel stack translate-history-card">
          <div className="translate-output-head">
            <h3>Memory Feed</h3>
            <span className="badge">{history.length} entries</span>
          </div>
          {history.length === 0 && <p className="translate-empty-history">Your recent translations will appear here.</p>}
          {history.length > 0 && (
            <div className="translate-history-list">
              {history.map((entry) => (
                <article key={entry.id} className="translate-history-item">
                  <p className="translate-history-meta">
                    {entry.kind.toUpperCase()} | {entry.sourceLang.toUpperCase()} {"->"} {entry.targetLang.toUpperCase()} |{" "}
                    {new Date(entry.createdAt).toLocaleTimeString()}
                  </p>
                  <p>{entry.inputText}</p>
                  <p className="translate-history-out">{entry.outputText}</p>
                  {shouldShowEngineBadge(entry.engine) && (
                    <span className={`badge translate-engine-badge ${resolveEngineClass(entry.engine)}`}>
                      {resolveEngineLabel(entry.engine)}
                    </span>
                  )}
                </article>
              ))}
            </div>
          )}
        </aside>
      </section>
    </section>
  );
}
