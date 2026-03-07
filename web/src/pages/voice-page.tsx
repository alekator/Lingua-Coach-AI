import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import type { VoiceMessageResponse } from "../api/types";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";
import { FilePicker } from "../components/file-picker";
import { AudioRecorder } from "../components/audio-recorder";
import { AudioPlayer } from "../components/audio-player";

function extractCoachTarget(text: string): string {
  const marker = "You should say:";
  const index = text.indexOf(marker);
  if (index < 0) return "";
  return text.slice(index + marker.length).trim().replace(/\.$/, "");
}

const SPEAKING_CHALLENGES: Record<string, string[]> = {
  en: [
    "I usually start my day with tea and a short walk.",
    "Could you tell me where the nearest pharmacy is?",
    "I am practicing English because I want to travel confidently.",
    "Yesterday I cooked dinner and watched a documentary.",
    "Please speak a bit slower, I am still learning.",
  ],
  ru: [
    "Сегодня я хочу потренировать произношение сложных слов.",
    "Подскажите, пожалуйста, где находится ближайшая остановка?",
    "Я учу язык каждый день по тридцать минут.",
    "Вчера мы встретились с друзьями и долго разговаривали.",
    "Мне нужно объяснить свою идею коротко и понятно.",
  ],
  de: [
    "Ich lerne jeden Tag Deutsch und mache kleine Fortschritte.",
    "Könnten Sie bitte langsamer sprechen?",
    "Gestern habe ich mit meiner Familie zu Abend gegessen.",
    "Ich möchte am Wochenende einen neuen Ort besuchen.",
    "Heute übe ich besonders die richtige Aussprache.",
  ],
  es: [
    "Estoy practicando mi pronunciación con frases cortas.",
    "¿Podría repetir la pregunta más despacio, por favor?",
    "Ayer estudié una hora y aprendí palabras nuevas.",
    "Quiero hablar con más confianza en conversaciones reales.",
    "Hoy voy a describir mi rutina diaria con claridad.",
  ],
  fr: [
    "Je m'entraîne à parler plus clairement chaque jour.",
    "Pouvez-vous parler un peu plus lentement, s'il vous plaît ?",
    "Hier, j'ai étudié et j'ai révisé du vocabulaire.",
    "Je veux améliorer mon accent pour mieux communiquer.",
    "Aujourd'hui, je vais raconter ma journée en détail.",
  ],
  pt: [
    "Estou praticando minha pronúncia com frases curtas.",
    "Você pode falar mais devagar, por favor?",
    "Ontem eu estudei e revisei novas palavras.",
    "Quero falar com mais confiança no trabalho.",
    "Hoje vou descrever minha rotina com clareza.",
  ],
};

type VoiceAttempt = {
  id: string;
  transcript: string;
  overallScore: number;
  createdAt: string;
};

export function VoicePage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const targetLang = useAppStore((s) => s.activeWorkspaceTargetLang) ?? "en";
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<VoiceMessageResponse | null>(null);
  const [progress, setProgress] = useState<Awaited<ReturnType<typeof api.voiceProgress>> | null>(null);
  const [progressError, setProgressError] = useState("");
  const [error, setError] = useState("");
  const [practicePhrase, setPracticePhrase] = useState("");
  const [challengeSentence, setChallengeSentence] = useState("");
  const [coachTarget, setCoachTarget] = useState("");
  const [attempts, setAttempts] = useState<VoiceAttempt[]>([]);
  const [busy, setBusy] = useState(false);
  const pushToast = useToastStore((s) => s.push);
  const attemptStorageKey = `voice-lab:v1:user:${userId}`;

  useEffect(() => {
    let active = true;
    api
      .voiceProgress(userId)
      .then((payload) => {
        if (!active) return;
        setProgress(payload);
        setProgressError("");
      })
      .catch((err) => {
        if (!active) return;
        setProgressError(getErrorMessage(err));
      });
    return () => {
      active = false;
    };
  }, [userId]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(attemptStorageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw) as VoiceAttempt[];
      if (!Array.isArray(parsed)) return;
      setAttempts(
        parsed
          .filter((item) => item && typeof item.id === "string" && typeof item.transcript === "string")
          .slice(0, 16),
      );
    } catch {
      // ignore malformed storage
    }
  }, [attemptStorageKey]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(attemptStorageKey, JSON.stringify(attempts.slice(0, 16)));
    } catch {
      // ignore storage limits
    }
  }, [attemptStorageKey, attempts]);

  const latestScore = result?.pronunciation_rubric?.overall_score ?? attempts[0]?.overallScore ?? 0;
  const averageScore = useMemo(() => {
    if (!attempts.length) return 0;
    return Math.round(attempts.reduce((acc, row) => acc + row.overallScore, 0) / attempts.length);
  }, [attempts]);
  const bestScore = useMemo(() => {
    if (!attempts.length) return 0;
    return Math.max(...attempts.map((row) => row.overallScore));
  }, [attempts]);
  const trendLabel = progress?.trend ?? "stable";
  const trendToneClass = trendLabel === "improving" ? "good" : trendLabel === "declining" ? "alert" : "neutral";
  const chartPoints = (progress?.points ?? []).slice(-10);
  const challengePool = SPEAKING_CHALLENGES[targetLang] ?? SPEAKING_CHALLENGES.en;

  useEffect(() => {
    setChallengeSentence(challengePool[0] ?? "");
  }, [targetLang, challengePool]);

  function scoreToLevel(score: number) {
    if (score >= 75) return "solid";
    if (score >= 45) return "developing";
    return "needs work";
  }

  function generateChallengeSentence() {
    if (!challengePool.length) return;
    if (challengePool.length === 1) {
      setChallengeSentence(challengePool[0]);
      return;
    }
    let next = challengePool[Math.floor(Math.random() * challengePool.length)];
    if (next === challengeSentence) {
      const alternatives = challengePool.filter((item) => item !== challengeSentence);
      next = alternatives[Math.floor(Math.random() * alternatives.length)] ?? next;
    }
    setChallengeSentence(next);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    try {
      const response = await api.voiceMessage({
        file,
        user_id: userId,
        target_lang: targetLang,
        language_hint: targetLang,
      });
      setResult(response);
      setCoachTarget(extractCoachTarget(response.teacher_text));
      if (response.pronunciation_rubric?.overall_score != null) {
        setAttempts((prev) =>
          [
            {
              id: `attempt-${Date.now()}`,
              transcript: response.transcript,
              overallScore: Math.round(response.pronunciation_rubric?.overall_score ?? 0),
              createdAt: new Date().toISOString(),
            },
            ...prev,
          ].slice(0, 16),
        );
      }
      setError("");
      pushToast("success", "Voice message processed");
      try {
        const payload = await api.voiceProgress(userId);
        setProgress(payload);
        setProgressError("");
      } catch (err) {
        setProgressError(getErrorMessage(err));
      }
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel stack voice-page">
      <header className="voice-hero panel">
        <div>
          <h2>Voice Studio</h2>
          <p>Practice language: {targetLang.toUpperCase()}.</p>
          <p>Record one short attempt, get coach feedback, and iterate with one focused retry.</p>
        </div>
        <div className="voice-hero-chips">
          <span className="badge">Latest: {latestScore}/100</span>
          <span className="badge">Avg: {averageScore || "n/a"}</span>
          <span className={`badge voice-trend-badge ${trendToneClass}`}>Trend: {trendLabel}</span>
        </div>
      </header>

      <article className="panel voice-challenge-card">
        <div className="voice-challenge-head">
          <div>
            <h3>Sentence Challenge</h3>
            <p>Get a random line in your study language and pronounce it clearly.</p>
          </div>
          <button type="button" className="cta-secondary" onClick={generateChallengeSentence}>
            New sentence
          </button>
        </div>
        <p className="voice-challenge-text">{challengeSentence || "Press New sentence to generate a speaking prompt."}</p>
        <div className="voice-challenge-actions">
          <button
            type="button"
            onClick={() => {
              if (!challengeSentence.trim()) return;
              setPracticePhrase(challengeSentence);
              pushToast("info", "Challenge line moved to retry field");
            }}
            disabled={!challengeSentence.trim()}
          >
            Use for retry
          </button>
        </div>
      </article>

      <section className="voice-grid">
        <article className="panel stack voice-main-card">
          <form className="panel stack voice-input-card" onSubmit={onSubmit}>
            <h3>Coach Voice Practice</h3>
            <label>
              Practice phrase (optional retry line)
              <input
                placeholder="Example: I went to school yesterday."
                value={practicePhrase}
                onChange={(e) => setPracticePhrase(e.target.value)}
              />
            </label>
            {practicePhrase && <p className="voice-retry-plan">Retry plan: say this phrase clearly in your next recording.</p>}
            <label>
              Upload voice sample (10-45 sec)
              <FilePicker
                id="voice-sample-file"
                ariaLabel="Upload voice sample (10-45 sec)"
                accept="audio/*"
                onFileChange={setFile}
              />
            </label>
            <label>
              Or record with microphone
              <AudioRecorder onRecordedFile={setFile} />
            </label>
            <button type="submit" className="cta-primary" disabled={!file || busy}>
              {busy ? "Analyzing..." : "Analyze voice"}
            </button>
          </form>

          {error && <ErrorState text={error} />}

          {result && (
            <article className="panel stack voice-feedback-card">
              <div className="voice-feedback-head">
                <h3>Coach feedback</h3>
                <span className="badge">
                  {Math.round(result.pronunciation_rubric?.overall_score ?? latestScore)} •{" "}
                  {result.pronunciation_rubric?.level_band ?? scoreToLevel(latestScore)}
                </span>
              </div>
              <p className="voice-transcript-line">
                <strong>Transcript:</strong> {result.transcript}
              </p>
              <p>
                <strong>Coach:</strong> {result.teacher_text}
              </p>
              <p>
                <strong>Pronunciation tip:</strong> {result.pronunciation_feedback}
              </p>
              {result.pronunciation_rubric && (
                <>
                  <div className="voice-skill-bars">
                    {[
                      { label: "Fluency", value: result.pronunciation_rubric.fluency },
                      { label: "Clarity", value: result.pronunciation_rubric.clarity },
                      { label: "Grammar", value: result.pronunciation_rubric.grammar_accuracy },
                      { label: "Vocabulary", value: result.pronunciation_rubric.vocabulary_range },
                      { label: "Confidence", value: result.pronunciation_rubric.confidence },
                    ].map((row) => (
                      <div key={row.label} className="voice-skill-row">
                        <p>
                          <span>{row.label}</span>
                          <strong>{Math.round(row.value)}</strong>
                        </p>
                        <div className="progress-meter">
                          <span style={{ width: `${Math.max(2, Math.min(100, row.value))}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="voice-tip-list">
                    {result.pronunciation_rubric.actionable_tips.map((tip, idx) => (
                      <p key={`voice-tip-${idx}`}>- {tip}</p>
                    ))}
                  </div>
                </>
              )}
              <AudioPlayer audioUrl={result.audio_url} label="Coach audio reply" />
              {coachTarget && (
                <button
                  type="button"
                  className="cta-secondary"
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
        </article>

        <aside className="panel stack voice-analytics-card">
          <h3>Dynamic metrics</h3>
          <div className="voice-kpi-grid">
            <article>
              <p>Latest score</p>
              <strong>{latestScore || "n/a"}</strong>
            </article>
            <article>
              <p>Average score</p>
              <strong>{averageScore || "n/a"}</strong>
            </article>
            <article>
              <p>Best score</p>
              <strong>{bestScore || "n/a"}</strong>
            </article>
            <article>
              <p>Mistakes (7d)</p>
              <strong>{progress?.pronunciation_mistakes_7d ?? "n/a"}</strong>
            </article>
          </div>

          <article className="voice-trend-card">
            <p>Speaking trend</p>
            <div className="voice-sparkline" aria-label="Speaking trend sparkline">
              {chartPoints.length > 0 ? (
                chartPoints.map((point) => (
                  <span
                    key={`${point.date}-${point.speaking_score}`}
                    title={`${point.date}: ${point.speaking_score}`}
                    style={{ height: `${Math.max(8, Math.min(100, point.speaking_score))}%` }}
                  />
                ))
              ) : (
                <small>No trend points yet.</small>
              )}
            </div>
            {progress?.recommendation && <small>{progress.recommendation}</small>}
            {progressError && <small className="status warning">Progress metric unavailable: {progressError}</small>}
          </article>

          <article className="voice-attempts-card">
            <div className="voice-feedback-head">
              <p>Recent attempts</p>
              <span className="badge">{attempts.length}</span>
            </div>
            {attempts.length === 0 && <small>No attempts yet. Submit your first sample.</small>}
            {attempts.length > 0 && (
              <div className="voice-attempts-list">
                {attempts.slice(0, 6).map((item) => (
                  <article key={item.id}>
                    <p>
                      <strong>{item.overallScore}</strong> / 100
                    </p>
                    <small>{new Date(item.createdAt).toLocaleString()}</small>
                    <p>{item.transcript}</p>
                  </article>
                ))}
              </div>
            )}
          </article>
        </aside>
      </section>
    </section>
  );
}
