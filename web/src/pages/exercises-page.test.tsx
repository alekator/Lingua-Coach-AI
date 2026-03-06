import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ExercisesPage } from "./exercises-page";

const routerFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

const mocks = vi.hoisted(() => ({
  coachErrorBank: vi.fn(),
  generateExercises: vi.fn(),
  gradeExercises: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    coachErrorBank: mocks.coachErrorBank,
    generateExercises: mocks.generateExercises,
    gradeExercises: mocks.gradeExercises,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (selector: (state: { userId: number }) => unknown) => selector({ userId: 1 }),
}));

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) =>
    selector({ push: mocks.pushToast }),
}));

function renderPage(initialEntries: string[] = ["/app/exercises"]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter future={routerFuture} initialEntries={initialEntries}>
        <ExercisesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ExercisesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.coachErrorBank.mockResolvedValue({
      user_id: 1,
      items: [
        {
          category: "grammar",
          occurrences: 3,
          latest_bad: "I goed",
          latest_good: "I went",
          latest_explanation: "Irregular verb form",
          last_seen_at: "2026-03-06T00:00:00Z",
          drill_prompt: "Rewrite 3 short lines fixing 'I goed' -> 'I went'.",
          suggested_route: "/app/exercises",
        },
      ],
    });
    mocks.generateExercises.mockResolvedValue({
      items: [
        { id: "ex-1", type: "fill_blank", prompt: "Fill in", expected_answer: "went" },
      ],
    });
    mocks.gradeExercises.mockResolvedValue({
      score: 1,
      max_score: 1,
      details: { "ex-1": true },
      rubric: {},
    });
  });

  it("uses error bank shortcut to generate targeted drill", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Recurring Error Focus")).toBeInTheDocument();
      expect(screen.getByText(/grammar \(3x\): I goed -> I went/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Use this drill" }));

    await waitFor(() => {
      expect(mocks.generateExercises).toHaveBeenCalledWith({
        user_id: 1,
        exercise_type: "fill_blank",
        topic: "grammar",
        count: 3,
      });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Exercises generated for grammar");
    });
  });

  it("auto-generates drill from topic query param for one-click next action", async () => {
    renderPage(["/app/exercises?topic=pronunciation"]);

    await waitFor(() => {
      expect(mocks.generateExercises).toHaveBeenCalledWith({
        user_id: 1,
        exercise_type: "fill_blank",
        topic: "pronunciation",
        count: 3,
      });
    });
  });
});
