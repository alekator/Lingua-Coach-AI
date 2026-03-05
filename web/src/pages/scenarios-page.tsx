import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { useAppStore } from "../store/app-store";

export function ScenariosPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [selectionResult, setSelectionResult] = useState("");
  const scenarios = useQuery({
    queryKey: ["scenarios"],
    queryFn: api.scenarios,
  });

  async function onSelect(scenarioId: string) {
    const response = await api.selectScenario({ user_id: userId, scenario_id: scenarioId });
    setSelectionResult(`Session ${response.session_id} started in mode ${response.mode}`);
  }

  return (
    <section className="panel stack">
      <h2>Scenarios</h2>
      {scenarios.isPending && <p>Loading scenarios...</p>}
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
      {selectionResult && <p>{selectionResult}</p>}
    </section>
  );
}
