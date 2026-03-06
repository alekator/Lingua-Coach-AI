import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenariosPage } from "./scenarios-page";

const mocks = vi.hoisted(() => ({
  scenarios: vi.fn(),
  coachSessionToday: vi.fn(),
  selectScenario: vi.fn(),
  scenarioScript: vi.fn(),
  scenarioTurn: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    scenarios: mocks.scenarios,
    coachSessionToday: mocks.coachSessionToday,
    selectScenario: mocks.selectScenario,
    scenarioScript: mocks.scenarioScript,
    scenarioTurn: mocks.scenarioTurn,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (selector: (state: { userId: number; dailyMinutes: number }) => unknown) =>
    selector({ userId: 1, dailyMinutes: 15 }),
}));

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) =>
    selector({ push: mocks.pushToast }),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ScenariosPage />
    </QueryClientProvider>,
  );
}

describe("ScenariosPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.scenarios.mockResolvedValue({
      items: [
        {
          id: "job-interview",
          title: "Job Interview",
          description: "Interview practice.",
          required_level: "B1",
          unlocked: true,
          gate_reason: null,
        },
        {
          id: "coffee-shop",
          title: "Coffee Shop",
          description: "Daily ordering.",
          required_level: "A1",
          unlocked: false,
          gate_reason: "Unlock at A1+ with avg skill >= 25 (now A1, avg 10).",
        },
      ],
    });
    mocks.coachSessionToday.mockResolvedValue({
      user_id: 1,
      time_budget_minutes: 15,
      focus: ["interview", "grammar", "vocab"],
      steps: [],
    });
    mocks.selectScenario.mockResolvedValue({
      session_id: 88,
      mode: "scenario:job-interview",
    });
    mocks.scenarioScript.mockResolvedValue({
      scenario_id: "job-interview",
      title: "Job Interview",
      description: "Interview practice.",
      steps: [
        {
          id: "intro",
          coach_prompt: "Introduce yourself in 2-3 sentences for this role.",
          expected_keywords: ["experience", "role", "skills"],
          tip: "Keep structure.",
        },
      ],
    });
    mocks.scenarioTurn.mockResolvedValue({
      scenario_id: "job-interview",
      step_id: "intro",
      score: 2,
      max_score: 3,
      feedback: "Good attempt: add one more concrete detail from the prompt.",
      next_step_id: null,
      next_prompt: null,
      done: true,
      suggested_reply: "Try again using: experience, role",
    });
  });

  it("shows recommended scenario and runs roleplay turn flow", async () => {
    renderPage();

    await waitFor(() => {
      expect(mocks.scenarios).toHaveBeenCalledWith(1);
      expect(screen.getByText("Recommended for today")).toBeInTheDocument();
      expect(screen.getByText(/Coach cue: today focus is interview, grammar, vocab/i)).toBeInTheDocument();
      expect(screen.getByText("Required level: B1")).toBeInTheDocument();
      expect(screen.getByText(/Locked:/)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Locked by mastery" })).toBeDisabled();
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Start coached roleplay" })[0]);

    await waitFor(() => {
      expect(mocks.selectScenario).toHaveBeenCalledWith({ user_id: 1, scenario_id: "job-interview" });
      expect(mocks.scenarioScript).toHaveBeenCalledWith("job-interview", 1);
      expect(screen.getByText(/Coach session ready:/i)).toBeInTheDocument();
      expect(screen.getByText("Active Roleplay Step")).toBeInTheDocument();
      expect(screen.getByText("Introduce yourself in 2-3 sentences for this role.")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Your response"), { target: { value: "I have experience in support role" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit roleplay turn" }));

    await waitFor(() => {
      expect(mocks.scenarioTurn).toHaveBeenCalledWith({
        user_id: 1,
        scenario_id: "job-interview",
        step_id: "intro",
        user_text: "I have experience in support role",
      });
      expect(screen.getByText("Step score: 2/3")).toBeInTheDocument();
    });
  });
});
