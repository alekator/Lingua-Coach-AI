import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { OnboardingPage } from "./onboarding-page";

const routerFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  pushToast: vi.fn(),
  setBootstrapState: vi.fn(),
  setCoachPrefs: vi.fn(),
  placementStart: vi.fn(),
  placementAnswer: vi.fn(),
  placementFinish: vi.fn(),
  planToday: vi.fn(),
  profileSetup: vi.fn(),
  openaiKeyStatus: vi.fn(),
  openaiKeySet: vi.fn(),
  debugOpenai: vi.fn(),
  aiRuntimeStatus: vi.fn(),
  aiRuntimeSet: vi.fn(),
  languageCapabilities: vi.fn(),
  activeWorkspaceNativeLang: null as string | null,
  activeWorkspaceTargetLang: null as string | null,
  activeWorkspaceGoal: null as string | null,
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
      activeWorkspaceNativeLang: mocks.activeWorkspaceNativeLang,
      activeWorkspaceTargetLang: mocks.activeWorkspaceTargetLang,
      activeWorkspaceGoal: mocks.activeWorkspaceGoal,
      setBootstrapState: mocks.setBootstrapState,
      setCoachPrefs: mocks.setCoachPrefs,
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
      aiRuntimeStatus: mocks.aiRuntimeStatus,
      aiRuntimeSet: mocks.aiRuntimeSet,
      languageCapabilities: mocks.languageCapabilities,
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
    mocks.activeWorkspaceNativeLang = null;
    mocks.activeWorkspaceTargetLang = null;
    mocks.activeWorkspaceGoal = null;
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
    mocks.aiRuntimeStatus.mockResolvedValue({
      llm_provider: "openai",
      asr_provider: "openai",
      tts_provider: "openai",
      llm: { provider: "openai", status: "disabled", message: "LLM provider is OpenAI" },
      asr: { provider: "openai", status: "disabled", message: "ASR provider is OpenAI" },
      tts: { provider: "openai", status: "disabled", message: "TTS provider is OpenAI" },
    });
    mocks.aiRuntimeSet.mockResolvedValue({
      llm_provider: "openai",
      asr_provider: "openai",
      tts_provider: "openai",
      llm: { provider: "openai", status: "disabled", message: "LLM provider is OpenAI" },
      asr: { provider: "openai", status: "disabled", message: "ASR provider is OpenAI" },
      tts: { provider: "openai", status: "disabled", message: "TTS provider is OpenAI" },
    });
    mocks.languageCapabilities.mockResolvedValue({
      native_lang: "ru",
      target_lang: "en",
      text_supported: true,
      asr_supported: true,
      tts_supported: true,
      voice_supported: true,
      recommendation: "Full mode: chat, translate, and voice are available.",
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
      skill_map: {
        grammar: 42,
        vocab: 48,
        speaking: 50,
        listening: 57,
      },
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
      <MemoryRouter future={routerFuture}>
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
      expect(screen.getByText("You're in. First result is ready.")).toBeInTheDocument();
      expect(screen.getByText("Your level:")).toBeInTheDocument();
      expect(screen.getByText("3 personal focus areas")).toBeInTheDocument();
      expect(screen.getByText("Personal plan for today")).toBeInTheDocument();
      expect(screen.getByText("Grammar precision")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Start my personalized session" }));
    expect(mocks.navigate).toHaveBeenCalledWith("/app/session");
  });

  it("blocks start when native and target language are equal", async () => {
    render(
      <MemoryRouter future={routerFuture}>
        <OnboardingPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Onboarding target language"), { target: { value: "ru" } });
    fireEvent.click(screen.getByRole("button", { name: "Start coaching placement" }));

    await waitFor(() => {
      expect(mocks.placementStart).not.toHaveBeenCalled();
      expect(screen.getByText("Native and target language must be different.")).toBeInTheDocument();
    });
  });

  it("supports preset and swap for onboarding language pair", async () => {
    render(
      <MemoryRouter future={routerFuture}>
        <OnboardingPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mocks.openaiKeyStatus).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByLabelText("Onboarding preset DE -> EN"));
    expect(screen.getByLabelText("Onboarding native language")).toHaveValue("de");
    expect(screen.getByLabelText("Onboarding target language")).toHaveValue("en");

    fireEvent.click(screen.getByLabelText("Onboarding swap languages"));
    expect(screen.getByLabelText("Onboarding native language")).toHaveValue("en");
    expect(screen.getByLabelText("Onboarding target language")).toHaveValue("de");
  });

  it("shows first-time hint for a new active workspace", async () => {
    mocks.activeWorkspaceNativeLang = "de";
    mocks.activeWorkspaceTargetLang = "en";
    mocks.activeWorkspaceGoal = "job";

    render(
      <MemoryRouter future={routerFuture}>
        <OnboardingPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("New learning space detected")).toBeInTheDocument();
      expect(
        screen.getByText("This language pair is new for you. Complete the short placement to unlock this space."),
      ).toBeInTheDocument();
    });
  });

  it("allows switching onboarding runtime mode to local", async () => {
    mocks.aiRuntimeSet.mockResolvedValue({
      llm_provider: "local",
      asr_provider: "local",
      tts_provider: "local",
      llm: { provider: "local", status: "ok", message: "ready" },
      asr: { provider: "local", status: "ok", message: "ready" },
      tts: { provider: "local", status: "ok", message: "ready" },
    });

    render(
      <MemoryRouter future={routerFuture}>
        <OnboardingPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mocks.aiRuntimeStatus).toHaveBeenCalledWith(false);
    });

    fireEvent.change(screen.getByLabelText("AI runtime mode"), { target: { value: "local" } });
    fireEvent.click(screen.getByRole("button", { name: "Save runtime mode" }));

    await waitFor(() => {
      expect(mocks.aiRuntimeSet).toHaveBeenCalledWith({
        llm_provider: "local",
        asr_provider: "local",
        tts_provider: "local",
      });
      expect(screen.getByText("OpenAI API key (optional in local mode)")).toBeInTheDocument();
    });
  });
});
