import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent } from "@testing-library/react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DashboardPage } from "./dashboard-page";

const mocks = vi.hoisted(() => ({
  progressSummary: vi.fn(),
  progressWeeklyGoal: vi.fn(),
  progressWeeklyGoalSet: vi.fn(),
  planToday: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    progressSummary: mocks.progressSummary,
    progressWeeklyGoal: mocks.progressWeeklyGoal,
    progressWeeklyGoalSet: mocks.progressWeeklyGoalSet,
    planToday: mocks.planToday,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (selector: (state: { userId: number }) => unknown) => selector({ userId: 1 }),
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
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.progressSummary.mockResolvedValue({
      streak_days: 3,
      minutes_practiced: 24,
      words_learned: 8,
      speaking: 52,
      listening: 48,
      grammar: 46,
      vocab: 55,
      reading: 51,
      writing: 47,
    });
    mocks.planToday.mockResolvedValue({
      user_id: 1,
      time_budget_minutes: 15,
      focus: ["travel", "grammar", "vocab"],
      tasks: ["5 min: SRS vocab review (due cards: 3)", "5 min: targeted correction drill (grammar)", "5 min: scenario practice (vocab)"],
      adaptation_notes: ["Low recent consistency detected; plan uses shorter high-impact blocks."],
    });
    mocks.progressWeeklyGoal.mockResolvedValue({
      user_id: 1,
      target_minutes: 120,
      completed_minutes: 24,
      remaining_minutes: 96,
      completion_percent: 20,
      is_completed: false,
    });
    mocks.progressWeeklyGoalSet.mockResolvedValue({
      user_id: 1,
      target_minutes: 150,
      completed_minutes: 24,
      remaining_minutes: 126,
      completion_percent: 16,
      is_completed: false,
    });
  });

  it("renders adaptive notes in today plan and updates weekly goal", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Today Coaching Plan (15 min)")).toBeInTheDocument();
      expect(
        screen.getByText("Adaptation: Low recent consistency detected; plan uses shorter high-impact blocks."),
      ).toBeInTheDocument();
      expect(screen.getByText("Weekly Goal Tracker")).toBeInTheDocument();
      expect(screen.getByText("Progress: 24/120 min (20%)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Save weekly goal" }));
    await waitFor(() => {
      expect(mocks.progressWeeklyGoalSet).toHaveBeenCalledWith({ user_id: 1, target_minutes: 120 });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Weekly goal updated");
    });
  });
});
