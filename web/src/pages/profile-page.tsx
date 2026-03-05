import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useAppStore } from "../store/app-store";

export function ProfilePage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const skillMap = useQuery({
    queryKey: ["skill-map", userId],
    queryFn: () => api.progressSkillMap(userId),
  });
  const streak = useQuery({
    queryKey: ["streak", userId],
    queryFn: () => api.progressStreak(userId),
  });

  return (
    <section className="panel stack">
      <h2>Profile & Progress</h2>
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
