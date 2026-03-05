import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState } from "../components/feedback";
import { LanguagePicker } from "../components/language-picker";
import { getErrorMessage } from "../lib/errors";
import { normalizeLanguageCode } from "../lib/languages";
import type { PlanTodayResponse } from "../api/types";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

function inferLikelyErrors(skillMap: Record<string, number>): string[] {
  const ranked = Object.entries(skillMap)
    .sort((a, b) => a[1] - b[1])
    .slice(0, 3)
    .map(([skill]) => skill);
  const templates: Record<string, string> = {
    grammar: "Verb tense and sentence structure slips in longer answers.",
    vocab: "Limited active vocabulary for specific real-life situations.",
    speaking: "Short hesitant phrasing without enough detail.",
    listening: "Missing key details in fast natural speech.",
    writing: "Inconsistent clarity and connector usage in written replies.",
    reading: "Difficulty with complex sentence meaning and intent.",
  };
  return ranked.map((skill) => templates[skill] ?? "Inconsistent language control under pressure.");
}

export function OnboardingPage() {
  const navigate = useNavigate();
  const userId = useAppStore((s) => s.userId) ?? 1;
  const activeWorkspaceNativeLang = useAppStore((s) => s.activeWorkspaceNativeLang);
  const activeWorkspaceTargetLang = useAppStore((s) => s.activeWorkspaceTargetLang);
  const activeWorkspaceGoal = useAppStore((s) => s.activeWorkspaceGoal);
  const setBootstrapState = useAppStore((s) => s.setBootstrapState);
  const setCoachPrefs = useAppStore((s) => s.setCoachPrefs);
  const [nativeLang, setNativeLang] = useState(activeWorkspaceNativeLang ?? "ru");
  const [targetLang, setTargetLang] = useState(activeWorkspaceTargetLang ?? "en");
  const [goal, setGoal] = useState(activeWorkspaceGoal ?? "travel");
  const [dailyMinutes, setDailyMinutes] = useState(15);
  const [strictness, setStrictness] = useState<"low" | "medium" | "high">("medium");
  const [apiKey, setApiKey] = useState("");
  const [keyStatus, setKeyStatus] = useState<"checking" | "configured" | "missing">("checking");
  const [keyHint, setKeyHint] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [questionIndex, setQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [recommendedLevel, setRecommendedLevel] = useState<string | null>(null);
  const [starterErrors, setStarterErrors] = useState<string[]>([]);
  const [starterPlan, setStarterPlan] = useState<PlanTodayResponse | null>(null);
  const [showWowResult, setShowWowResult] = useState(false);
  const [error, setError] = useState("");
  const pushToast = useToastStore((s) => s.push);

  useEffect(() => {
    let active = true;
    async function loadKeyStatus() {
      try {
        const status = await api.openaiKeyStatus();
        if (!active) return;
        setKeyStatus(status.configured ? "configured" : "missing");
        setKeyHint(status.masked ? `Configured: ${status.masked}` : "No API key configured yet.");
      } catch {
        if (!active) return;
        setKeyStatus("missing");
        setKeyHint("Failed to load key status.");
      }
    }
    loadKeyStatus();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (sessionId || showWowResult) return;
    if (activeWorkspaceNativeLang) {
      setNativeLang(activeWorkspaceNativeLang);
    }
    if (activeWorkspaceTargetLang) {
      setTargetLang(activeWorkspaceTargetLang);
    }
    if (activeWorkspaceGoal) {
      setGoal(activeWorkspaceGoal);
    }
  }, [activeWorkspaceGoal, activeWorkspaceNativeLang, activeWorkspaceTargetLang, sessionId, showWowResult]);

  async function onSaveApiKey() {
    if (!apiKey.trim()) return;
    setSubmitting(true);
    try {
      const status = await api.openaiKeySet({ api_key: apiKey.trim() });
      const debug = await api.debugOpenai();
      setKeyStatus(status.configured ? "configured" : "missing");
      setKeyHint(`${status.masked ?? "Configured"} | Probe: ${debug.status}`);
      setApiKey("");
      pushToast("success", "OpenAI key saved and verified");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function onStart() {
    setSubmitting(true);
    try {
      const normalizedNative = normalizeLanguageCode(nativeLang);
      const normalizedTarget = normalizeLanguageCode(targetLang);
      if (!normalizedNative || !normalizedTarget) {
        throw new Error("Please choose both native and target languages.");
      }
      if (normalizedNative === normalizedTarget) {
        throw new Error("Native and target language must be different.");
      }
      if (keyStatus !== "configured") {
        pushToast("info", "You can continue without key, but AI quality will be limited.");
      }
      const started = await api.placementStart({
        user_id: userId,
        native_lang: normalizedNative,
        target_lang: normalizedTarget,
      });
      setError("");
      setSessionId(started.session_id);
      setQuestion(started.question);
      setQuestionIndex(started.question_index);
      setTotalQuestions(started.total_questions);
      pushToast("info", "Placement test started");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function onAnswer(event: FormEvent) {
    event.preventDefault();
    if (!sessionId) return;
    setSubmitting(true);
    try {
      const accepted = await api.placementAnswer({ session_id: sessionId, answer });
      setAnswer("");
      if (accepted.done) {
        const finished = await api.placementFinish({ session_id: sessionId });
        const profile = await api.profileSetup({
          user_id: userId,
          native_lang: normalizeLanguageCode(nativeLang),
          target_lang: normalizeLanguageCode(targetLang),
          level: finished.level,
          goal,
          preferences: { strictness, daily_minutes: dailyMinutes },
        });
        const resolvedUserId = profile.user_id;
        const plan = await api.planToday(resolvedUserId, dailyMinutes);
        setCoachPrefs({ strictness, dailyMinutes });
        setRecommendedLevel(finished.level);
        setStarterErrors(inferLikelyErrors(finished.skill_map));
        setStarterPlan(plan);
        setShowWowResult(true);
        setBootstrapState({
          userId: resolvedUserId,
          hasProfile: true,
          activeWorkspaceNativeLang: normalizeLanguageCode(nativeLang),
          activeWorkspaceTargetLang: normalizeLanguageCode(targetLang),
          activeWorkspaceGoal: goal || null,
        });
        pushToast("success", `Placement complete: ${finished.level}`);
        return;
      }
      setQuestion(accepted.next_question ?? "");
      setQuestionIndex(accepted.next_question_index ?? questionIndex + 1);
      setError("");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel">
      <h2>First Launch Setup</h2>
      {showWowResult && (
        <article className="panel stack">
          <h3>Your quick coach result</h3>
          <p>Your detected level: {recommendedLevel}</p>
          <h4>Top 3 focus errors</h4>
          {starterErrors.map((item) => (
            <p key={item}>- {item}</p>
          ))}
          <h4>Your personal plan for today</h4>
          {starterPlan?.tasks.map((task) => (
            <p key={task}>- {task}</p>
          ))}
          <button type="button" onClick={() => navigate("/app")}>
            Start my first session
          </button>
        </article>
      )}
      {!sessionId && (
        <form className="stack" onSubmit={(event) => event.preventDefault()}>
          <p>Let your coach calibrate your starting point. Set languages and complete a quick placement test.</p>
          <LanguagePicker label="Native language" value={nativeLang} onChange={setNativeLang} />
          <LanguagePicker label="Target language" value={targetLang} onChange={setTargetLang} />
          <label>
            Goal
            <input value={goal} onChange={(e) => setGoal(e.target.value)} />
          </label>
          <label>
            Daily study minutes
            <input
              type="number"
              min={5}
              max={120}
              value={dailyMinutes}
              onChange={(e) => setDailyMinutes(Number(e.target.value || 15))}
            />
          </label>
          <label>
            Feedback strictness
            <select value={strictness} onChange={(e) => setStrictness(e.target.value as "low" | "medium" | "high")}>
              <option value="low">Low (soft)</option>
              <option value="medium">Medium</option>
              <option value="high">High (strict)</option>
            </select>
          </label>
          <label>
            OpenAI API key
            <input
              type="password"
              placeholder="sk-..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </label>
          <p>{keyStatus === "checking" ? "Checking key status..." : keyHint}</p>
          <button disabled={submitting || !apiKey.trim()} type="button" onClick={onSaveApiKey}>
            {submitting ? "Saving key..." : "Save and verify key"}
          </button>
          <button disabled={submitting} type="button" onClick={onStart}>
            {submitting ? "Starting..." : "Start coaching placement"}
          </button>
        </form>
      )}
      {sessionId && (
        <form onSubmit={onAnswer} className="stack">
          <p>
            Question {questionIndex + 1} / {totalQuestions}
          </p>
          <p>{question}</p>
          <label>
            Your answer
            <input value={answer} onChange={(e) => setAnswer(e.target.value)} />
          </label>
          <button disabled={submitting || !answer.trim()} type="submit">
            {submitting ? "Checking..." : "Submit to coach"}
          </button>
        </form>
      )}
      {recommendedLevel && <p>Detected level: {recommendedLevel}</p>}
      {error && <ErrorState text={error} />}
    </section>
  );
}
