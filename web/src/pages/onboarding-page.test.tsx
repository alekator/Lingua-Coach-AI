import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { OnboardingPage } from "./onboarding-page";

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  pushToast: vi.fn(),
  setBootstrapState: vi.fn(),
  placementStart: vi.fn(),
  placementAnswer: vi.fn(),
  placementFinish: vi.fn(),
  planToday: vi.fn(),
  profileSetup: vi.fn(),
  openaiKeyStatus: vi.fn(),
  openaiKeySet: vi.fn(),
  debugOpenai: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
  };
});

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) =>
    selector({ push: mocks.pushToast }),
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (
    selector: (state: {
      userId: number;
      hasProfile: boolean;
      activeWorkspaceNativeLang: string | null;
      activeWorkspaceTargetLang: string | null;
      activeWorkspaceGoal: string | null;
      setBootstrapState: typeof mocks.setBootstrapState;
      setCoachPrefs: (...args: unknown[]) => void;
    }) => unknown,
  ) =>
    selector({
      userId: 1,
      hasProfile: false,
      activeWorkspaceNativeLang: null,
      activeWorkspaceTargetLang: null,
      activeWorkspaceGoal: null,
      setBootstrapState: mocks.setBootstrapState,
      setCoachPrefs: vi.fn(),
    }),
}));

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return {
    ...actual,
    api: {
      openaiKeyStatus: mocks.openaiKeyStatus,
      openaiKeySet: mocks.openaiKeySet,
      debugOpenai: mocks.debugOpenai,
      placementStart: mocks.placementStart,
      placementAnswer: mocks.placementAnswer,
      placementFinish: mocks.placementFinish,
      planToday: mocks.planToday,
      profileSetup: mocks.profileSetup,
    },
  };
});

describe("OnboardingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.openaiKeyStatus.mockResolvedValue({
      configured: false,
      source: "none",
      masked: null,
    });
    mocks.openaiKeySet.mockResolvedValue({
      configured: true,
      source: "env",
      masked: "sk-t...7890",
    });
    mocks.debugOpenai.mockResolvedValue({
      status: "ok",
      detail: "OpenAI reachable",
    });
  });

  it("runs placement flow and navigates to app", async () => {
    mocks.placementStart.mockResolvedValue({
      session_id: 77,
      question_index: 0,
      question: "Tell me about your day.",
      total_questions: 1,
    });
    mocks.placementAnswer.mockResolvedValue({
      session_id: 77,
      accepted_question_index: 0,
      done: true,
      next_question_index: null,
      next_question: null,
    });
    mocks.placementFinish.mockResolvedValue({
      session_id: 77,
      level: "B1",
      avg_score: 0.61,
      skill_map: {},
    });
    mocks.profileSetup.mockResolvedValue({
      user_id: 101,
      native_lang: "ru",
      target_lang: "en",
      level: "B1",
      goal: "travel",
      preferences: {},
    });
    mocks.planToday.mockResolvedValue({
      user_id: 101,
      time_budget_minutes: 15,
      focus: ["travel", "grammar", "vocab"],
      tasks: ["5 min: quick review (travel)", "5 min: targeted correction drill (grammar)", "5 min: scenario practice (vocab)"],
      adaptation_notes: [],
    });

    render(
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Start coaching placement" }));

    await waitFor(() => {
      expect(screen.getByText("Tell me about your day.")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Your answer"), {
      target: { value: "I usually start with coffee and then work." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit to coach" }));

    await waitFor(() => {
      expect(mocks.placementFinish).toHaveBeenCalledWith({ session_id: 77 });
      expect(mocks.profileSetup).toHaveBeenCalledWith(
        expect.objectContaining({
          user_id: 1,
          level: "B1",
          native_lang: "ru",
          target_lang: "en",
        }),
      );
      expect(mocks.planToday).toHaveBeenCalledWith(101, 15);
      expect(mocks.setBootstrapState).toHaveBeenCalledWith(
        expect.objectContaining({ userId: 101, hasProfile: true }),
      );
      expect(screen.getByText("Your quick coach result")).toBeInTheDocument();
      expect(screen.getByText("Your detected level: B1")).toBeInTheDocument();
      expect(screen.getByText("Top 3 focus errors")).toBeInTheDocument();
      expect(screen.getByText("Your personal plan for today")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Start my first session" }));
    expect(mocks.navigate).toHaveBeenCalledWith("/app");
  });

  it("blocks start when native and target language are equal", async () => {
    render(
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Target language"), { target: { value: "ru" } });
    fireEvent.click(screen.getByRole("button", { name: "Start coaching placement" }));

    await waitFor(() => {
      expect(mocks.placementStart).not.toHaveBeenCalled();
      expect(screen.getByText("Native and target language must be different.")).toBeInTheDocument();
    });
  });
});
