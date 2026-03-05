import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenariosPage } from "./scenarios-page";

const mocks = vi.hoisted(() => ({
  scenarios: vi.fn(),
  coachSessionToday: vi.fn(),
  selectScenario: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    scenarios: mocks.scenarios,
    coachSessionToday: mocks.coachSessionToday,
    selectScenario: mocks.selectScenario,
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
        { id: "job-interview", title: "Job Interview", description: "Interview practice." },
        { id: "coffee-shop", title: "Coffee Shop", description: "Daily ordering." },
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
  });

  it("shows recommended scenario and starts coached roleplay", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Recommended for today")).toBeInTheDocument();
      expect(screen.getByText(/Coach cue: today focus is interview, grammar, vocab/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Start coached roleplay" })[0]);

    await waitFor(() => {
      expect(mocks.selectScenario).toHaveBeenCalledWith({ user_id: 1, scenario_id: "job-interview" });
      expect(screen.getByText(/Coach session ready:/i)).toBeInTheDocument();
    });
  });
});
