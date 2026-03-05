import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function ScenariosPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [selectionResult, setSelectionResult] = useState("");
  const [actionError, setActionError] = useState("");
  const pushToast = useToastStore((s) => s.push);
  const scenarios = useQuery({
    queryKey: ["scenarios"],
    queryFn: api.scenarios,
  });

  async function onSelect(scenarioId: string) {
    try {
      const response = await api.selectScenario({ user_id: userId, scenario_id: scenarioId });
      setSelectionResult(`Session ${response.session_id} started in mode ${response.mode}`);
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
      <h2>Scenarios</h2>
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
              <p>{item.description}</p>
              <button onClick={() => onSelect(item.id)} type="button">
                Start scenario
              </button>
            </article>
          ))}
        </div>
      )}
      {actionError && <ErrorState text={actionError} />}
      {selectionResult && <p>{selectionResult}</p>}
    </section>
  );
}
