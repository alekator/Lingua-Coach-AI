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
  profileSetup: vi.fn(),
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
    selector: (state: { userId: number; hasProfile: boolean; setBootstrapState: typeof mocks.setBootstrapState }) => unknown,
  ) =>
    selector({ userId: 1, hasProfile: false, setBootstrapState: mocks.setBootstrapState }),
}));

vi.mock("../api/client", () => ({
  api: {
    placementStart: mocks.placementStart,
    placementAnswer: mocks.placementAnswer,
    placementFinish: mocks.placementFinish,
    profileSetup: mocks.profileSetup,
  },
}));

describe("OnboardingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    mocks.profileSetup.mockResolvedValue({ ok: true });

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
      expect(mocks.setBootstrapState).toHaveBeenCalledWith({ userId: 1, hasProfile: true });
      expect(mocks.navigate).toHaveBeenCalledWith("/app");
    });
  });
});
