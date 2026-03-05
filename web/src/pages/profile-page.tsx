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
  const [saving, setSaving] = useState(false);
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

  return (
    <section className="panel stack">
      <h2>Profile & Progress</h2>
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
        </form>
      )}
      {saveError && <ErrorState text={saveError} />}
      {(streak.isPending || skillMap.isPending) && <LoadingState text="Loading profile analytics..." />}
      {(streak.isError || skillMap.isError) && <ErrorState text="Failed to load progress analytics." />}
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
    </section>
  );
}
