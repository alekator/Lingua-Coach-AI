import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ProfilePage } from "./profile-page";

const mocks = vi.hoisted(() => ({
  profileGet: vi.fn(),
  profileSetup: vi.fn(),
  bootstrap: vi.fn(),
  workspacesList: vi.fn(),
  workspaceCreate: vi.fn(),
  workspaceSwitch: vi.fn(),
  placementStart: vi.fn(),
  placementAnswer: vi.fn(),
  placementFinish: vi.fn(),
  progressSkillMap: vi.fn(),
  progressStreak: vi.fn(),
  progressJournal: vi.fn(),
  pushToast: vi.fn(),
  navigate: vi.fn(),
  setBootstrapState: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
  };
});

vi.mock("../api/client", () => ({
  api: {
    profileGet: mocks.profileGet,
    profileSetup: mocks.profileSetup,
    bootstrap: mocks.bootstrap,
    workspacesList: mocks.workspacesList,
    workspaceCreate: mocks.workspaceCreate,
    workspaceSwitch: mocks.workspaceSwitch,
    placementStart: mocks.placementStart,
    placementAnswer: mocks.placementAnswer,
    placementFinish: mocks.placementFinish,
    progressSkillMap: mocks.progressSkillMap,
    progressStreak: mocks.progressStreak,
    progressJournal: mocks.progressJournal,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (
    selector: (state: {
      userId: number;
      activeWorkspaceId: number;
      setBootstrapState: typeof mocks.setBootstrapState;
    }) => unknown,
  ) =>
    selector({ userId: 1, activeWorkspaceId: 1, setBootstrapState: mocks.setBootstrapState }),
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
      <ProfilePage />
    </QueryClientProvider>,
  );
}

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.profileGet.mockResolvedValue({
      user_id: 1,
      native_lang: "ru",
      target_lang: "en",
      level: "B1",
      goal: "work",
      preferences: { strictness: "medium" },
    });
    mocks.progressSkillMap.mockResolvedValue({
      speaking: 50,
      listening: 52,
      grammar: 48,
      vocab: 55,
      reading: 53,
      writing: 47,
    });
    mocks.progressStreak.mockResolvedValue({
      streak_days: 2,
      active_dates: ["2026-03-05", "2026-03-06"],
    });
    mocks.progressJournal.mockResolvedValue({
      weekly_minutes: 24,
      weekly_sessions: 3,
      weak_areas: ["grammar"],
      next_actions: ["Run one targeted drill for: grammar."],
      entries: [
        {
          session_id: 9,
          started_at: "2026-03-06",
          mode: "chat",
          messages_count: 4,
          completed: true,
        },
      ],
    });
    mocks.profileSetup.mockResolvedValue({});
    mocks.bootstrap.mockResolvedValue({
      user_id: 1,
      has_profile: true,
      needs_onboarding: false,
      next_step: "dashboard",
      owner_user_id: 1,
      active_workspace_id: 1,
    });
    mocks.workspacesList.mockResolvedValue({
      owner_user_id: 1,
      active_workspace_id: 1,
      items: [{ id: 1, native_lang: "ru", target_lang: "en", goal: "work", is_active: true }],
    });
    mocks.workspaceCreate.mockResolvedValue({
      id: 2,
      native_lang: "de",
      target_lang: "en",
      goal: "job",
      is_active: true,
      created_at: "2026-03-06T00:00:00Z",
      updated_at: "2026-03-06T00:00:00Z",
    });
    mocks.workspaceSwitch.mockResolvedValue({ active_workspace_id: 1, active_user_id: 1 });
    mocks.placementStart.mockResolvedValue({
      session_id: 11,
      question_index: 0,
      question: "Describe your last weekend.",
      total_questions: 1,
    });
    mocks.placementAnswer.mockResolvedValue({
      session_id: 11,
      accepted_question_index: 0,
      done: true,
      next_question_index: null,
      next_question: null,
    });
    mocks.placementFinish.mockResolvedValue({
      session_id: 11,
      level: "B2",
      avg_score: 0.78,
      skill_map: {},
    });
  });

  it("loads profile settings and saves edits", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByDisplayValue("ru")).toBeInTheDocument();
      expect(screen.getByText("Weekly Journal")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Profile goal"), { target: { value: "travel" } });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => {
      expect(mocks.profileSetup).toHaveBeenCalledWith(
        expect.objectContaining({
          user_id: 1,
          native_lang: "ru",
          target_lang: "en",
          level: "B1",
          goal: "travel",
        }),
      );
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Profile updated");
    });
  });

  it("retakes placement test and updates level", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByDisplayValue("B1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Recalibrate level" }));

    await waitFor(() => {
      expect(screen.getByText("Describe your last weekend.")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Your answer"), {
      target: { value: "I visited friends and watched a movie." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit answer" }));

    await waitFor(() => {
      expect(mocks.placementFinish).toHaveBeenCalledWith({ session_id: 11 });
      expect(mocks.profileSetup).toHaveBeenCalledWith(
        expect.objectContaining({
          user_id: 1,
          level: "B2",
        }),
      );
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Placement updated: B2");
    });
  });

  it("creates a new learning space and syncs bootstrap context", async () => {
    mocks.bootstrap.mockResolvedValue({
      user_id: 22,
      has_profile: false,
      needs_onboarding: true,
      next_step: "onboarding",
      owner_user_id: 1,
      active_workspace_id: 2,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Learning Spaces" })).toBeInTheDocument();
      expect(screen.getByLabelText("New native language")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("New native language"), { target: { value: "de" } });
    fireEvent.change(screen.getByLabelText("New target language"), { target: { value: "en" } });
    fireEvent.change(screen.getByLabelText("New space goal"), { target: { value: "job" } });
    fireEvent.click(screen.getByRole("button", { name: "Create and switch space" }));

    await waitFor(() => {
      expect(mocks.workspaceCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          native_lang: "de",
          target_lang: "en",
          goal: "job",
          make_active: true,
        }),
      );
      expect(mocks.setBootstrapState).toHaveBeenCalledWith(
        expect.objectContaining({
          userId: 22,
          hasProfile: false,
          activeWorkspaceId: 2,
        }),
      );
      expect(mocks.navigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });
});
