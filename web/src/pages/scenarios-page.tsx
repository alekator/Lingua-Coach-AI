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
  const [activeScenarioId, setActiveScenarioId] = useState("");
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [activeStepId, setActiveStepId] = useState("");
  const [activePrompt, setActivePrompt] = useState("");
  const [activeTip, setActiveTip] = useState("");
  const [turnAnswer, setTurnAnswer] = useState("");
  const [turnFeedback, setTurnFeedback] = useState("");
  const [turnScore, setTurnScore] = useState("");
  const pushToast = useToastStore((s) => s.push);
  const scenarios = useQuery({
    queryKey: ["scenarios", userId],
    queryFn: () => api.scenarios(userId),
  });
  const coachSession = useQuery({
    queryKey: ["coach-session-today", userId, dailyMinutes],
    queryFn: () => api.coachSessionToday(userId, dailyMinutes),
  });
  const scenarioTracks = useQuery({
    queryKey: ["coach-scenario-tracks", userId],
    queryFn: () => api.coachScenarioTracks(userId),
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
      const scenario = scenarios.data?.items.find((item) => item.id === scenarioId);
      if (scenario && !scenario.unlocked) {
        const msg = scenario.gate_reason || "Scenario is locked by mastery gate.";
        setActionError(msg);
        pushToast("info", msg);
        return;
      }
      const [response, script] = await Promise.all([
        api.selectScenario({ user_id: userId, scenario_id: scenarioId }),
        api.scenarioScript(scenarioId, userId),
      ]);
      const firstStep = script.steps[0];
      setActiveScenarioId(scenarioId);
      setActiveSessionId(response.session_id);
      setActiveStepId(firstStep?.id ?? "");
      setActivePrompt(firstStep?.coach_prompt ?? "");
      setActiveTip(firstStep?.tip ?? "");
      setTurnAnswer("");
      setTurnFeedback("");
      setTurnScore("");
      setSelectionResult(`Session ${response.session_id} started in mode ${response.mode}.`);
      setActionError("");
      pushToast("success", "Scenario session started");
    } catch (err) {
      const msg = getErrorMessage(err);
      setActionError(msg);
      pushToast("error", msg);
    }
  }

  async function onSubmitTurn() {
    if (!activeScenarioId || !activeStepId || !turnAnswer.trim()) return;
    try {
      const response = await api.scenarioTurn({
        user_id: userId,
        scenario_id: activeScenarioId,
        step_id: activeStepId,
        user_text: turnAnswer.trim(),
      });
      setTurnFeedback(response.feedback + (response.suggested_reply ? ` ${response.suggested_reply}` : ""));
      setTurnScore(`Step score: ${response.score}/${response.max_score}`);
      setTurnAnswer("");
      if (response.done) {
        if (activeSessionId) {
          try {
            await api.chatEnd({ session_id: activeSessionId });
            await scenarioTracks.refetch();
          } catch {
            // keep scenario completion UX even if close fails
          }
        }
        setActiveSessionId(null);
        setActiveStepId("");
        setActivePrompt("Scenario completed. Great work.");
        setActiveTip("Review feedback and replay scenario for fluency.");
        pushToast("success", "Roleplay scenario completed");
        return;
      }
      setActiveStepId(response.next_step_id ?? "");
      setActivePrompt(response.next_prompt ?? "");
      setActiveTip("Use one clear sentence, then add one detail.");
      pushToast("info", "Move to next roleplay step");
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
              <p>Required level: {item.required_level}</p>
              <p>{item.description}</p>
              {!item.unlocked && <p>Locked: {item.gate_reason ?? "Improve mastery to unlock."}</p>}
              <button onClick={() => onSelect(item.id)} type="button" disabled={!item.unlocked}>
                {item.unlocked ? "Start coached roleplay" : "Locked by mastery"}
              </button>
            </article>
          ))}
        </div>
      )}
      {scenarioTracks.isSuccess && scenarioTracks.data.items.length > 0 && (
        <article className="panel stack">
          <h3>Goal Scenario Tracks</h3>
          {scenarioTracks.data.items.map((track) => (
            <div key={track.track_id} className="panel stack">
              <p>
                <strong>{track.title}</strong> ({track.goal}) - {track.completed_steps}/{track.total_steps} (
                {track.completion_percent}%)
              </p>
              {track.next_scenario_id && <p>Next milestone scenario: {track.next_scenario_id}</p>}
              <p>
                Milestones:{" "}
                {track.milestones
                  .map((m) => `${m.title}: ${m.is_reached ? "done" : `need ${m.required_completed}`}`)
                  .join(" | ")}
              </p>
            </div>
          ))}
        </article>
      )}
      {activeScenarioId && (
        <article className="panel stack">
          <h3>Active Roleplay Step</h3>
          <p>{activePrompt}</p>
          {activeTip && <p>Coach tip: {activeTip}</p>}
          <label>
            Your response
            <input value={turnAnswer} onChange={(e) => setTurnAnswer(e.target.value)} />
          </label>
          <button type="button" onClick={onSubmitTurn} disabled={!activeStepId || !turnAnswer.trim()}>
            Submit roleplay turn
          </button>
          {turnScore && <p>{turnScore}</p>}
          {turnFeedback && <p>{turnFeedback}</p>}
        </article>
      )}
      {actionError && <ErrorState text={actionError} />}
      {selectionResult && <p>Coach session ready: {selectionResult}</p>}
    </section>
  );
}
