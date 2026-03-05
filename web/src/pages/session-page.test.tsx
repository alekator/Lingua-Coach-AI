import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionPage } from "./session-page";

const routerFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

const mocks = vi.hoisted(() => ({
  coachSessionToday: vi.fn(),
  coachSessionProgress: vi.fn(),
  coachSessionProgressUpsert: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    coachSessionToday: mocks.coachSessionToday,
    coachSessionProgress: mocks.coachSessionProgress,
    coachSessionProgressUpsert: mocks.coachSessionProgressUpsert,
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
      <MemoryRouter future={routerFuture}>
        <SessionPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SessionPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.coachSessionToday.mockResolvedValue({
      user_id: 1,
      time_budget_minutes: 15,
      focus: ["grammar", "vocab", "speaking"],
      steps: [
        { id: "warmup", title: "Warmup", description: "Warm up", route: "/app/grammar", duration_minutes: 2 },
        { id: "chat", title: "Coach Chat", description: "Chat loop", route: "/app/chat", duration_minutes: 5 },
      ],
    });
    mocks.coachSessionProgress.mockResolvedValue({
      user_id: 1,
      session_date: "2026-03-06",
      total_steps: 2,
      completed_steps: 1,
      completion_percent: 50,
      items: [
        { step_id: "warmup", title: "Warmup", status: "completed", started_at: "2026-03-06T10:00:00Z", completed_at: "2026-03-06T10:02:00Z" },
        { step_id: "chat", title: "Coach Chat", status: "pending", started_at: null, completed_at: null },
      ],
    });
    mocks.coachSessionProgressUpsert.mockResolvedValue({
      user_id: 1,
      session_date: "2026-03-06",
      total_steps: 2,
      completed_steps: 2,
      completion_percent: 100,
      items: [],
    });
  });

  it("renders progress and updates step status", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Progress: 1/2 steps (50%)")).toBeInTheDocument();
      expect(screen.getByText("Step 2: Coach Chat")).toBeInTheDocument();
      expect(screen.getByText("Status: pending")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Mark step completed" }));

    await waitFor(() => {
      expect(mocks.coachSessionProgressUpsert).toHaveBeenCalledWith({
        user_id: 1,
        step_id: "chat",
        status: "completed",
        time_budget_minutes: 15,
      });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Step marked as completed");
    });
  });
});
