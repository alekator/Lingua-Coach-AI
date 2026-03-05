import { useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function ProfilePage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [nativeLang, setNativeLang] = useState("");
  const [targetLang, setTargetLang] = useState("");
  const [level, setLevel] = useState("");
  const [goal, setGoal] = useState("");
  const [saveError, setSaveError] = useState("");
  const [placementError, setPlacementError] = useState("");
  const [saving, setSaving] = useState(false);
  const [retakeOpen, setRetakeOpen] = useState(false);
  const [retakeSessionId, setRetakeSessionId] = useState<number | null>(null);
  const [retakeQuestion, setRetakeQuestion] = useState("");
  const [retakeQuestionIndex, setRetakeQuestionIndex] = useState(0);
  const [retakeTotalQuestions, setRetakeTotalQuestions] = useState(0);
  const [retakeAnswer, setRetakeAnswer] = useState("");
  const [retakeBusy, setRetakeBusy] = useState(false);
  const pushToast = useToastStore((s) => s.push);
  const profile = useQuery({
    queryKey: ["profile", userId],
    queryFn: () => api.profileGet(userId),
  });
  const skillMap = useQuery({
    queryKey: ["skill-map", userId],
    queryFn: () => api.progressSkillMap(userId),
  });
  const streak = useQuery({
    queryKey: ["streak", userId],
    queryFn: () => api.progressStreak(userId),
  });
  const journal = useQuery({
    queryKey: ["progress-journal", userId],
    queryFn: () => api.progressJournal(userId),
  });

  useEffect(() => {
    if (!profile.data) return;
    setNativeLang(profile.data.native_lang);
    setTargetLang(profile.data.target_lang);
    setLevel(profile.data.level);
    setGoal(profile.data.goal ?? "");
  }, [profile.data]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api.profileSetup({
        user_id: userId,
        native_lang: nativeLang,
        target_lang: targetLang,
        level,
        goal,
        preferences: profile.data?.preferences ?? {},
      });
      setSaveError("");
      pushToast("success", "Profile updated");
      await profile.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setSaveError(msg);
      pushToast("error", msg);
    } finally {
      setSaving(false);
    }
  }

  async function onRetakeStart() {
    setRetakeBusy(true);
    try {
      const started = await api.placementStart({
        user_id: userId,
        native_lang: nativeLang,
        target_lang: targetLang,
      });
      setRetakeOpen(true);
      setRetakeSessionId(started.session_id);
      setRetakeQuestion(started.question);
      setRetakeQuestionIndex(started.question_index);
      setRetakeTotalQuestions(started.total_questions);
      setRetakeAnswer("");
      setPlacementError("");
      pushToast("info", "Placement retake started");
    } catch (err) {
      const msg = getErrorMessage(err);
      setPlacementError(msg);
      pushToast("error", msg);
    } finally {
      setRetakeBusy(false);
    }
  }

  async function onRetakeAnswer(event: FormEvent) {
    event.preventDefault();
    if (!retakeSessionId) return;
    setRetakeBusy(true);
    try {
      const accepted = await api.placementAnswer({
        session_id: retakeSessionId,
        answer: retakeAnswer,
      });
      setRetakeAnswer("");
      if (accepted.done) {
        const finished = await api.placementFinish({ session_id: retakeSessionId });
        await api.profileSetup({
          user_id: userId,
          native_lang: nativeLang,
          target_lang: targetLang,
          level: finished.level,
          goal,
          preferences: profile.data?.preferences ?? {},
        });
        setLevel(finished.level);
        setRetakeOpen(false);
        setRetakeSessionId(null);
        setRetakeQuestion("");
        setRetakeQuestionIndex(0);
        setRetakeTotalQuestions(0);
        setPlacementError("");
        pushToast("success", `Placement updated: ${finished.level}`);
        await skillMap.refetch();
        return;
      }
      setRetakeQuestion(accepted.next_question ?? "");
      setRetakeQuestionIndex(accepted.next_question_index ?? retakeQuestionIndex + 1);
      setPlacementError("");
    } catch (err) {
      const msg = getErrorMessage(err);
      setPlacementError(msg);
      pushToast("error", msg);
    } finally {
      setRetakeBusy(false);
    }
  }

  return (
    <section className="panel stack">
      <h2>Coach Profile & Progress</h2>
      <p>Set your learning preferences and track coach signals for steady progress.</p>
      {profile.isPending && <LoadingState text="Loading profile settings..." />}
      {profile.isError && <ErrorState text="Failed to load profile settings." />}
      {profile.isSuccess && (
        <form className="stack" onSubmit={onSave}>
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
          <button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save settings"}
          </button>
          <button
            type="button"
            disabled={retakeBusy || !nativeLang.trim() || !targetLang.trim()}
            onClick={onRetakeStart}
          >
            {retakeBusy && !retakeOpen ? "Starting..." : "Recalibrate level"}
          </button>
        </form>
      )}
      {saveError && <ErrorState text={saveError} />}
      {placementError && <ErrorState text={placementError} />}
      {retakeOpen && (
        <form className="panel stack" onSubmit={onRetakeAnswer}>
          <h3>Level Recalibration</h3>
          <p>
            Question {retakeQuestionIndex + 1} / {retakeTotalQuestions}
          </p>
          <p>{retakeQuestion}</p>
          <label>
            Your answer
            <input value={retakeAnswer} onChange={(e) => setRetakeAnswer(e.target.value)} />
          </label>
          <button type="submit" disabled={retakeBusy || !retakeAnswer.trim()}>
            {retakeBusy ? "Checking..." : "Submit answer"}
          </button>
        </form>
      )}
      {(streak.isPending || skillMap.isPending || journal.isPending) && (
        <LoadingState text="Loading profile analytics..." />
      )}
      {(streak.isError || skillMap.isError || journal.isError) && (
        <ErrorState text="Failed to load progress analytics." />
      )}
      {streak.isSuccess && skillMap.isSuccess && streak.data.streak_days === 0 && (
        <EmptyState text="No tracked activity yet. Start a lesson to populate progress." />
      )}
      {streak.isSuccess && (
        <article className="panel">
          <h3>Streak</h3>
          <p>{streak.data.streak_days} days</p>
          <p>Active dates: {streak.data.active_dates.join(", ") || "none"}</p>
        </article>
      )}
      {skillMap.isSuccess && (
        <article className="panel">
          <h3>Skill Map</h3>
          <p>Speaking: {skillMap.data.speaking}</p>
          <p>Listening: {skillMap.data.listening}</p>
          <p>Grammar: {skillMap.data.grammar}</p>
          <p>Vocab: {skillMap.data.vocab}</p>
          <p>Reading: {skillMap.data.reading}</p>
          <p>Writing: {skillMap.data.writing}</p>
        </article>
      )}
      {journal.isSuccess && (
        <article className="panel">
          <h3>Weekly Journal</h3>
          <p>
            Sessions: {journal.data.weekly_sessions} | Minutes: {journal.data.weekly_minutes}
          </p>
          <p>Weak areas: {journal.data.weak_areas.join(", ") || "none detected"}</p>
          <h4>Next actions</h4>
          <p>Coach recommendation: pick one action and complete it today.</p>
          {journal.data.next_actions.map((action) => (
            <p key={action}>- {action}</p>
          ))}
          <h4>Recent sessions</h4>
          {journal.data.entries.length === 0 && <p>No session history yet.</p>}
          {journal.data.entries.map((entry) => (
            <p key={entry.session_id}>
              #{entry.session_id} | {entry.started_at} | {entry.mode} | msgs: {entry.messages_count} |{" "}
              {entry.completed ? "completed" : "in progress"}
            </p>
          ))}
        </article>
      )}
    </section>
  );
}
