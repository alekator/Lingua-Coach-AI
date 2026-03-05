import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function ScenariosPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const dailyMinutes = useAppStore((s) => s.dailyMinutes);
  const [selectionResult, setSelectionResult] = useState("");
  const [actionError, setActionError] = useState("");
  const pushToast = useToastStore((s) => s.push);
  const scenarios = useQuery({
    queryKey: ["scenarios"],
    queryFn: api.scenarios,
  });
  const coachSession = useQuery({
    queryKey: ["coach-session-today", userId, dailyMinutes],
    queryFn: () => api.coachSessionToday(userId, dailyMinutes),
  });

  const recommendedScenarioId = useMemo(() => {
    const focus = coachSession.data?.focus ?? [];
    if (!focus.length) return null;
    if (focus.includes("interview")) return "job-interview";
    if (focus.includes("travel")) return "travel-hotel";
    if (focus.includes("speaking")) return "coffee-shop";
    if (focus.includes("grammar")) return "job-interview";
    return "coffee-shop";
  }, [coachSession.data]);

  async function onSelect(scenarioId: string) {
    try {
      const response = await api.selectScenario({ user_id: userId, scenario_id: scenarioId });
      setSelectionResult(`Session ${response.session_id} started in mode ${response.mode}. Open Coach Chat next.`);
      setActionError("");
      pushToast("success", "Scenario session started");
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    }
  }

  return (
    <section className="panel stack">
      <h2>Roleplay Scenarios</h2>
      <p>Choose one realistic situation and run a short coached roleplay.</p>
      {coachSession.isSuccess && (
        <p>Coach cue: today focus is {coachSession.data.focus.join(", ")}. Start with the recommended scenario.</p>
      )}
      {scenarios.isPending && <LoadingState text="Loading scenarios..." />}
      {scenarios.isError && <ErrorState text="Failed to load scenarios." />}
      {scenarios.isSuccess && scenarios.data.items.length === 0 && (
        <EmptyState text="No scenarios available yet." />
      )}
      {scenarios.isSuccess && (
        <div className="stack">
          {scenarios.data.items.map((item) => (
            <article key={item.id} className="panel">
              <h3>{item.title}</h3>
              {recommendedScenarioId === item.id && <p className="badge">Recommended for today</p>}
              <p>{item.description}</p>
              <button onClick={() => onSelect(item.id)} type="button">
                Start coached roleplay
              </button>
            </article>
          ))}
        </div>
      )}
      {actionError && <ErrorState text={actionError} />}
      {selectionResult && <p>Coach session ready: {selectionResult}</p>}
    </section>
  );
}
