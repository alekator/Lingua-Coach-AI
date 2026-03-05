import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAppStore } from "../store/app-store";

export function OnboardingPage() {
  const navigate = useNavigate();
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [nativeLang, setNativeLang] = useState("ru");
  const [targetLang, setTargetLang] = useState("en");
  const [level, setLevel] = useState("A2");
  const [goal, setGoal] = useState("travel");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    await api.profileSetup({
      user_id: userId,
      native_lang: nativeLang,
      target_lang: targetLang,
      level,
      goal,
      preferences: { strictness: "medium" },
    });
    navigate("/app");
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
    </section>
  );
}
