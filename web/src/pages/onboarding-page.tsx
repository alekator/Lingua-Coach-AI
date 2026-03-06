import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState } from "../components/feedback";
import { LanguagePairSelector } from "../components/language-pair-selector";
import { getErrorMessage } from "../lib/errors";
import { t, uiLocaleFromNativeLang } from "../lib/i18n";
import { normalizeLanguageCode } from "../lib/languages";
import type { PlanTodayResponse } from "../api/types";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

type StarterFocusItem = {
  skill: string;
  title: string;
  why: string;
  action: string;
};

function inferLikelyErrors(skillMap: Record<string, number>): StarterFocusItem[] {
  const ranked = Object.entries(skillMap)
    .sort((a, b) => a[1] - b[1])
    .slice(0, 3);
  const templates: Record<string, Omit<StarterFocusItem, "skill">> = {
    grammar: {
      title: "Grammar precision",
      why: "Verb tense and sentence structure slips in longer answers.",
      action: "Do one short correction drill and rewrite your line once.",
    },
    vocab: {
      title: "Active vocabulary",
      why: "Limited active vocabulary for specific real-life situations.",
      action: "Learn 3 practical words and use each in one sentence today.",
    },
    speaking: {
      title: "Speaking flow",
      why: "Short hesitant phrasing without enough detail.",
      action: "Record one 30-second answer and retry with one improvement.",
    },
    listening: {
      title: "Listening detail",
      why: "Missing key details in fast natural speech.",
      action: "Run one short listening/voice task and summarize in 1-2 lines.",
    },
    writing: {
      title: "Writing clarity",
      why: "Inconsistent clarity and connector usage in written replies.",
      action: "Write a compact paragraph with 2 connectors and self-correct.",
    },
    reading: {
      title: "Reading comprehension",
      why: "Difficulty with complex sentence meaning and intent.",
      action: "Read one short text and extract 3 key points.",
    },
  };
  return ranked.map(([skill]) => {
    const preset = templates[skill] ?? {
      title: "Language control",
      why: "Inconsistent language control under pressure.",
      action: "Do one compact drill and apply the feedback in your next reply.",
    };
    return { skill, ...preset };
  });
}

function levelMessage(level: string): string {
  const copy: Record<string, string> = {
    A1: "You can handle basic phrases. We will build confidence and useful daily patterns.",
    A2: "You already communicate in simple situations. Next step is smoother accuracy.",
    B1: "You can hold practical conversations. We will sharpen precision and fluency.",
    B2: "You express ideas well. Focus now is nuance, speed, and consistency.",
    C1: "You are advanced. We target polish, style, and domain-specific confidence.",
    C2: "You are near-native in many contexts. We optimize mastery and edge cases.",
  };
  return copy[level] ?? "You have a solid base. We will personalize the next high-impact steps.";
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
  const [keyStatus, setKeyStatus] = useState<"checking" | "configured" | "missing" | "invalid">("checking");
  const [keyHint, setKeyHint] = useState("");
  const [runtimeProvider, setRuntimeProvider] = useState<"openai" | "local">("openai");
  const [runtimeLoading, setRuntimeLoading] = useState(true);
  const [runtimeSaving, setRuntimeSaving] = useState(false);
  const [runtimeHint, setRuntimeHint] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [questionIndex, setQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [recommendedLevel, setRecommendedLevel] = useState<string | null>(null);
  const [starterErrors, setStarterErrors] = useState<StarterFocusItem[]>([]);
  const [placementAvgScore, setPlacementAvgScore] = useState<number | null>(null);
  const [starterPlan, setStarterPlan] = useState<PlanTodayResponse | null>(null);
  const [showWowResult, setShowWowResult] = useState(false);
  const [capabilityHint, setCapabilityHint] = useState("");
  const [error, setError] = useState("");
  const pushToast = useToastStore((s) => s.push);
  const locale = uiLocaleFromNativeLang(activeWorkspaceNativeLang);
  const firstTimeInCurrentSpace = Boolean(activeWorkspaceNativeLang && activeWorkspaceTargetLang);

  useEffect(() => {
    let active = true;
    async function loadKeyStatus() {
      try {
        const status = await api.openaiKeyStatus();
        if (!active) return;
        setKeyStatus(status.configured ? "configured" : "missing");
        if (!status.configured) {
          setKeyHint("No API key configured yet.");
        } else {
          const secureLabel = status.secure_storage ? "secure local storage" : "local storage";
          const persistLabel = status.persistent ? `persisted in ${secureLabel}` : "active for current session";
          setKeyHint(`Configured: ${status.masked ?? "hidden"} (${persistLabel})`);
        }
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
    let active = true;
    async function loadRuntimeStatus() {
      setRuntimeLoading(true);
      try {
        const status = await api.aiRuntimeStatus(false);
        if (!active) return;
        const unified =
          status.llm_provider === status.asr_provider && status.llm_provider === status.tts_provider
            ? status.llm_provider
            : "openai";
        setRuntimeProvider(unified);
        if (status.llm_provider === status.asr_provider && status.llm_provider === status.tts_provider) {
          setRuntimeHint(`Current runtime: ${status.llm_provider.toUpperCase()} (LLM/ASR/TTS)`);
        } else {
          setRuntimeHint(
            `Current runtime is mixed (LLM=${status.llm_provider}, ASR=${status.asr_provider}, TTS=${status.tts_provider}). Onboarding will use a unified mode.`,
          );
        }
      } catch {
        if (!active) return;
        setRuntimeHint("Failed to load runtime status. Using OpenAI mode by default.");
      } finally {
        if (active) setRuntimeLoading(false);
      }
    }
    loadRuntimeStatus();
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

  useEffect(() => {
    let active = true;
    const native = normalizeLanguageCode(nativeLang);
    const target = normalizeLanguageCode(targetLang);
    if (!native || !target || native === target) {
      setCapabilityHint("");
      return () => {
        active = false;
      };
    }
    api
      .languageCapabilities(native, target)
      .then((caps) => {
        if (!active) return;
        setCapabilityHint(caps.recommendation);
      })
      .catch(() => {
        if (!active) return;
        setCapabilityHint("Could not load language capabilities right now.");
      });
    return () => {
      active = false;
    };
  }, [nativeLang, targetLang]);

  async function onSaveApiKey() {
    if (!apiKey.trim()) return;
    setSubmitting(true);
    try {
      const status = await api.openaiKeySet({ api_key: apiKey.trim() });
      const debug = await api.debugOpenai();
      setKeyStatus(status.configured ? "configured" : "missing");
      const secureLabel = status.secure_storage ? "secure local storage" : "local storage";
      setKeyHint(`${status.masked ?? "Configured"} | ${secureLabel} | Probe: ${debug.status}`);
      setApiKey("");
      pushToast("success", "OpenAI key saved and verified");
    } catch (err) {
      const msg = getErrorMessage(err);
      setKeyStatus("invalid");
      setKeyHint("Key save/verification failed. App can continue in lightweight mode.");
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
      if (runtimeProvider === "openai" && keyStatus !== "configured") {
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

  async function onSaveRuntimeProvider() {
    setRuntimeSaving(true);
    try {
      await api.aiRuntimeSet({
        llm_provider: runtimeProvider,
        asr_provider: runtimeProvider,
        tts_provider: runtimeProvider,
      });
      setRuntimeHint(`Runtime mode saved: ${runtimeProvider.toUpperCase()} (LLM/ASR/TTS)`);
      pushToast("success", `Runtime mode saved: ${runtimeProvider.toUpperCase()}`);
      setError("");
    } catch (err) {
      const msg = getErrorMessage(err);
      setRuntimeHint("Failed to save runtime mode.");
      setError(msg);
      pushToast("error", msg);
    } finally {
      setRuntimeSaving(false);
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
        setPlacementAvgScore(finished.avg_score);
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
      <h2>{t(locale, "onboarding_title")}</h2>
      {showWowResult && (
        <article className="panel stack">
          <h3>You're in. First result is ready.</h3>
          <p>
            <strong>Your level:</strong> {recommendedLevel}
            {typeof placementAvgScore === "number" && ` (${Math.round(placementAvgScore * 100)}% confidence)`}
          </p>
          {recommendedLevel && <p>{levelMessage(recommendedLevel)}</p>}
          <h4>3 personal focus areas</h4>
          {starterErrors.map((item) => (
            <div key={item.skill} className="panel stack">
              <p>
                <strong>{item.title}</strong>
              </p>
              <p>Why: {item.why}</p>
              <p>Today action: {item.action}</p>
            </div>
          ))}
          <h4>Personal plan for today</h4>
          {starterPlan && (
            <p>
              Mode: {starterPlan.time_budget_minutes} min | Focus: {starterPlan.focus.join(", ")}
            </p>
          )}
          {starterPlan?.tasks.map((task) => (
            <p key={task}>- {task}</p>
          ))}
          <button
            type="button"
            className="cta-primary"
            onClick={() => navigate("/app/session")}
          >
            Start my personalized session
          </button>
          <button type="button" className="cta-secondary" onClick={() => navigate("/app")}>
            Open dashboard
          </button>
        </article>
      )}
      {!sessionId && (
        <form className="stack" onSubmit={(event) => event.preventDefault()}>
          {firstTimeInCurrentSpace && (
            <article className="panel stack">
              <h3>{t(locale, "onboarding_new_space_title")}</h3>
              <p>{t(locale, "onboarding_new_space_note")}</p>
            </article>
          )}
          <p>Let your coach calibrate your starting point. Set languages and complete a quick placement test.</p>
          <LanguagePairSelector
            nativeLang={nativeLang}
            targetLang={targetLang}
            onNativeLangChange={setNativeLang}
            onTargetLangChange={setTargetLang}
            ariaPrefix="Onboarding"
          />
          {capabilityHint && <p>{capabilityHint}</p>}
          <label>
            AI runtime mode
            <select
              value={runtimeProvider}
              onChange={(e) => setRuntimeProvider(e.target.value as "openai" | "local")}
              disabled={runtimeLoading || runtimeSaving || submitting}
            >
              <option value="openai">OpenAI (cloud API)</option>
              <option value="local">Local models (on this machine)</option>
            </select>
          </label>
          <button
            type="button"
            onClick={onSaveRuntimeProvider}
            disabled={runtimeLoading || runtimeSaving || submitting}
          >
            {runtimeSaving ? "Saving runtime..." : "Save runtime mode"}
          </button>
          <p>{runtimeLoading ? "Loading runtime mode..." : runtimeHint}</p>
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
            OpenAI API key {runtimeProvider === "local" ? "(optional in local mode)" : ""}
            <input
              type="password"
              placeholder="sk-..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </label>
          {(runtimeProvider === "openai" || keyStatus === "invalid") && (keyStatus === "missing" || keyStatus === "invalid") && (
            <article className="panel stack" aria-live="polite">
              <strong>
                {keyStatus === "invalid" ? "OpenAI key is invalid or unavailable." : "OpenAI key is not configured."}
              </strong>
              <p>
                You can continue onboarding now. App will use lightweight fallback responses until key access works.
              </p>
            </article>
          )}
          <p>{keyStatus === "checking" ? "Checking key status..." : keyHint}</p>
          <button disabled={submitting || !apiKey.trim()} type="button" onClick={onSaveApiKey}>
            {submitting ? "Saving key..." : t(locale, "onboarding_save_key")}
          </button>
          <button disabled={submitting} type="button" onClick={onStart}>
            {submitting ? "Starting..." : t(locale, "onboarding_start")}
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
