import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function OnboardingPage() {
  const navigate = useNavigate();
  const userId = useAppStore((s) => s.userId) ?? 1;
  const setBootstrapState = useAppStore((s) => s.setBootstrapState);
  const [nativeLang, setNativeLang] = useState("ru");
  const [targetLang, setTargetLang] = useState("en");
  const [goal, setGoal] = useState("travel");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [questionIndex, setQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [recommendedLevel, setRecommendedLevel] = useState<string | null>(null);
  const [error, setError] = useState("");
  const pushToast = useToastStore((s) => s.push);

  async function onStart() {
    setSubmitting(true);
    try {
      const started = await api.placementStart({
        user_id: userId,
        native_lang: nativeLang,
        target_lang: targetLang,
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
        await api.profileSetup({
          user_id: userId,
          native_lang: nativeLang,
          target_lang: targetLang,
          level: finished.level,
          goal,
          preferences: { strictness: "medium" },
        });
        setRecommendedLevel(finished.level);
        setBootstrapState({ userId, hasProfile: true });
        pushToast("success", `Placement complete: ${finished.level}`);
        navigate("/app");
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
      {!sessionId && (
        <form className="stack" onSubmit={(event) => event.preventDefault()}>
          <p>Set languages, then pass a short placement test to detect your starting level.</p>
          <label>
            Native language
            <input value={nativeLang} onChange={(e) => setNativeLang(e.target.value)} />
          </label>
          <label>
            Target language
            <input value={targetLang} onChange={(e) => setTargetLang(e.target.value)} />
          </label>
          <label>
            Goal
            <input value={goal} onChange={(e) => setGoal(e.target.value)} />
          </label>
          <button disabled={submitting} type="button" onClick={onStart}>
            {submitting ? "Starting..." : "Start placement test"}
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
            {submitting ? "Checking..." : "Submit answer"}
          </button>
        </form>
      )}
      {recommendedLevel && <p>Detected level: {recommendedLevel}</p>}
      {error && <ErrorState text={error} />}
    </section>
  );
}
