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
  const [nativeLang, setNativeLang] = useState("ru");
  const [targetLang, setTargetLang] = useState("en");
  const [level, setLevel] = useState("A2");
  const [goal, setGoal] = useState("travel");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const pushToast = useToastStore((s) => s.push);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.profileSetup({
        user_id: userId,
        native_lang: nativeLang,
        target_lang: targetLang,
        level,
        goal,
        preferences: { strictness: "medium" },
      });
      setError("");
      pushToast("success", "Profile saved");
      navigate("/app");
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
      <p>Set your learner profile once. You can adjust it later in profile settings.</p>
      <form onSubmit={onSubmit} className="stack">
        <label>
          Native language
          <input value={nativeLang} onChange={(e) => setNativeLang(e.target.value)} />
        </label>
        <label>
          Target language
          <input value={targetLang} onChange={(e) => setTargetLang(e.target.value)} />
        </label>
        <label>
          CEFR level
          <input value={level} onChange={(e) => setLevel(e.target.value)} />
        </label>
        <label>
          Goal
          <input value={goal} onChange={(e) => setGoal(e.target.value)} />
        </label>
        <button disabled={submitting} type="submit">
          {submitting ? "Saving..." : "Save and continue"}
        </button>
      </form>
      {error && <ErrorState text={error} />}
    </section>
  );
}
