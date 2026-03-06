import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ProfilePage } from "./profile-page";

const mocks = vi.hoisted(() => ({
  profileGet: vi.fn(),
  profileSetup: vi.fn(),
  appReset: vi.fn(),
  appBackupExport: vi.fn(),
  appBackupRestore: vi.fn(),
  bootstrap: vi.fn(),
  workspacesList: vi.fn(),
  workspaceCreate: vi.fn(),
  workspaceUpdate: vi.fn(),
  workspaceSwitch: vi.fn(),
  workspaceDelete: vi.fn(),
  placementStart: vi.fn(),
  placementAnswer: vi.fn(),
  placementFinish: vi.fn(),
  progressSkillMap: vi.fn(),
  progressStreak: vi.fn(),
  progressSkillTree: vi.fn(),
  progressJournal: vi.fn(),
  progressTimeline: vi.fn(),
  usageBudgetStatus: vi.fn(),
  usageBudgetSet: vi.fn(),
  openaiKeyStatus: vi.fn(),
  openaiKeySet: vi.fn(),
  aiRuntimeStatus: vi.fn(),
  aiRuntimeSet: vi.fn(),
  debugOpenai: vi.fn(),
  pushToast: vi.fn(),
  navigate: vi.fn(),
  setBootstrapState: vi.fn(),
  setTheme: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
    useLocation: () => ({ hash: "" }),
  };
});

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return {
    ...actual,
    api: {
      profileGet: mocks.profileGet,
      profileSetup: mocks.profileSetup,
      appReset: mocks.appReset,
      appBackupExport: mocks.appBackupExport,
      appBackupRestore: mocks.appBackupRestore,
      bootstrap: mocks.bootstrap,
      workspacesList: mocks.workspacesList,
      workspaceCreate: mocks.workspaceCreate,
      workspaceUpdate: mocks.workspaceUpdate,
      workspaceSwitch: mocks.workspaceSwitch,
      workspaceDelete: mocks.workspaceDelete,
      placementStart: mocks.placementStart,
      placementAnswer: mocks.placementAnswer,
      placementFinish: mocks.placementFinish,
      progressSkillMap: mocks.progressSkillMap,
      progressStreak: mocks.progressStreak,
      progressSkillTree: mocks.progressSkillTree,
      progressJournal: mocks.progressJournal,
      progressTimeline: mocks.progressTimeline,
      usageBudgetStatus: mocks.usageBudgetStatus,
      usageBudgetSet: mocks.usageBudgetSet,
      openaiKeyStatus: mocks.openaiKeyStatus,
      openaiKeySet: mocks.openaiKeySet,
      aiRuntimeStatus: mocks.aiRuntimeStatus,
      aiRuntimeSet: mocks.aiRuntimeSet,
      debugOpenai: mocks.debugOpenai,
    },
  };
});

vi.mock("../store/app-store", () => ({
  useAppStore: (
    selector: (state: {
      userId: number;
      activeWorkspaceId: number;
      setBootstrapState: typeof mocks.setBootstrapState;
      theme: "light" | "dark-elegant";
      setTheme: typeof mocks.setTheme;
    }) => unknown,
  ) =>
    selector({
      userId: 1,
      activeWorkspaceId: 1,
      setBootstrapState: mocks.setBootstrapState,
      theme: "light",
      setTheme: mocks.setTheme,
    }),
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
    Object.defineProperty(URL, "createObjectURL", {
      writable: true,
      value: vi.fn(() => "blob:test-backup"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      writable: true,
      value: vi.fn(() => undefined),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    mocks.profileGet.mockResolvedValue({
      user_id: 1,
      native_lang: "ru",
      target_lang: "en",
      level: "B1",
      goal: "work",
      preferences: { strictness: "medium" },
    });
    mocks.progressSkillMap.mockResolvedValue({
      speaking: 31.6,
      listening: 31.9,
      grammar: 35.5,
      vocab: 36.6,
      reading: 31.9,
      writing: 33.3,
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
    mocks.progressTimeline.mockResolvedValue({
      user_id: 1,
      workspace_id: null,
      skill_filter: null,
      activity_type_filter: null,
      items: [
        {
          id: "session-1",
          workspace_id: 1,
          workspace_label: "ru->en",
          activity_type: "chat",
          skill_tags: ["grammar", "speaking"],
          title: "Coach chat session",
          detail: "Mode: chat. Messages: 4.",
          happened_at: "2026-03-06T12:00:00+00:00",
        },
      ],
    });
    mocks.progressSkillTree.mockResolvedValue({
      user_id: 1,
      current_level: "A2",
      estimated_level_from_skills: "A2",
      avg_skill_score: 33.46,
      next_target_level: "B1",
      items: [
        {
          level: "A1",
          status: "in_progress",
          progress_percent: 75,
          closed_criteria: ["Avg skill >= 20"],
          remaining_criteria: ["Complete 4 sessions"],
        },
        {
          level: "A2",
          status: "in_progress",
          progress_percent: 25,
          closed_criteria: ["Reach 3 sessions this week"],
          remaining_criteria: ["Avg skill >= 35"],
        },
      ],
    });
    mocks.profileSetup.mockResolvedValue({});
    mocks.usageBudgetStatus.mockResolvedValue({
      user_id: 1,
      daily_token_cap: 12000,
      weekly_token_cap: 60000,
      warning_threshold: 0.8,
      daily_used_tokens: 1500,
      weekly_used_tokens: 6000,
      daily_remaining_tokens: 10500,
      weekly_remaining_tokens: 54000,
      daily_warning: false,
      weekly_warning: false,
      blocked: false,
    });
    mocks.usageBudgetSet.mockResolvedValue({
      user_id: 1,
      daily_token_cap: 10000,
      weekly_token_cap: 50000,
      warning_threshold: 0.85,
      daily_used_tokens: 1500,
      weekly_used_tokens: 6000,
      daily_remaining_tokens: 8500,
      weekly_remaining_tokens: 44000,
      daily_warning: false,
      weekly_warning: false,
      blocked: false,
    });
    mocks.openaiKeyStatus.mockResolvedValue({
      configured: false,
      source: "none",
      masked: null,
      persistent: false,
      secure_storage: true,
    });
    mocks.openaiKeySet.mockResolvedValue({
      configured: true,
      source: "secure_storage",
      masked: "sk-...1234",
      persistent: true,
      secure_storage: true,
    });
    mocks.aiRuntimeStatus.mockResolvedValue({
      llm_provider: "openai",
      asr_provider: "openai",
      tts_provider: "openai",
      llm: {
        provider: "openai",
        status: "disabled",
        message: "LLM provider is OpenAI",
        model_path: null,
        model_exists: false,
        dependency_available: true,
        device: "cpu",
        load_ms: null,
        probe_ms: null,
      },
      asr: {
        provider: "openai",
        status: "disabled",
        message: "ASR provider is OpenAI",
        model_path: null,
        model_exists: false,
        dependency_available: true,
        device: "cpu",
        load_ms: null,
        probe_ms: null,
      },
      tts: {
        provider: "openai",
        status: "disabled",
        message: "TTS provider is OpenAI",
        model_path: null,
        model_exists: false,
        dependency_available: true,
        device: "cpu",
        load_ms: null,
        probe_ms: null,
      },
    });
    mocks.aiRuntimeSet.mockResolvedValue({
      llm_provider: "local",
      asr_provider: "local",
      tts_provider: "local",
      llm: {
        provider: "local",
        status: "ok",
        message: "ready",
        model_path: "F:/models/qwen.gguf",
        model_exists: true,
        dependency_available: true,
        device: "cpu",
        load_ms: 100,
        probe_ms: 150,
      },
      asr: {
        provider: "local",
        status: "ok",
        message: "ready",
        model_path: "F:/models/whisper-small",
        model_exists: true,
        dependency_available: true,
        device: "cpu",
        load_ms: 120,
        probe_ms: 180,
      },
      tts: {
        provider: "local",
        status: "ok",
        message: "ready",
        model_path: "F:/models/qwen3-tts",
        model_exists: true,
        dependency_available: true,
        device: "cpu",
        load_ms: 220,
        probe_ms: 260,
      },
    });
    mocks.debugOpenai.mockResolvedValue({
      status: "ok",
      detail: "reachable",
    });
    mocks.appReset.mockResolvedValue({
      status: "ok",
      deleted_users: 2,
      deleted_workspaces: 1,
      deleted_profiles: 1,
      deleted_vocab_items: 3,
      deleted_chat_sessions: 1,
      openai_key_cleared: true,
    });
    mocks.appBackupExport.mockResolvedValue({
      version: 1,
      exported_at: "2026-03-06T00:00:00Z",
      snapshot: { users: [{ id: 1 }] },
    });
    mocks.appBackupRestore.mockResolvedValue({
      status: "ok",
      restored_tables: { users: 1 },
    });
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
      items: [
        { id: 1, native_lang: "ru", target_lang: "en", goal: "work", is_active: true },
        { id: 2, native_lang: "de", target_lang: "en", goal: "job", is_active: false },
      ],
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
    mocks.workspaceUpdate.mockResolvedValue({
      id: 2,
      native_lang: "de",
      target_lang: "en",
      goal: "updated goal",
      is_active: false,
      created_at: "2026-03-06T00:00:00Z",
      updated_at: "2026-03-06T00:00:00Z",
    });
    mocks.workspaceSwitch.mockResolvedValue({ active_workspace_id: 1, active_user_id: 1 });
    mocks.workspaceDelete.mockResolvedValue({ deleted_workspace_id: 2, active_workspace_id: 1 });
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

  it("renders redesigned profile sections", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Coach Profile" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Learning Spaces" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Skill Map" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "CEFR Skill Tree" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Weekly Journal" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Learning Timeline" })).toBeInTheDocument();
    });
  });

  it("retakes placement test and updates level", async () => {
    renderPage();

    const recalibrateButton = await screen.findByRole("button", { name: "Recalibrate" });
    await waitFor(() => {
      expect(recalibrateButton).toBeEnabled();
    });
    fireEvent.click(recalibrateButton);

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
      expect(screen.getByLabelText("New space native language")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("New space native language"), { target: { value: "de" } });
    fireEvent.change(screen.getByLabelText("New space target language"), { target: { value: "en" } });
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

  it("prevents creating a space with identical language pair", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByLabelText("New space native language")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("New space native language"), { target: { value: "ru" } });
    fireEvent.change(screen.getByLabelText("New space target language"), { target: { value: "ru" } });
    fireEvent.click(screen.getByRole("button", { name: "Create and switch space" }));

    await waitFor(() => {
      expect(mocks.workspaceCreate).not.toHaveBeenCalled();
      expect(screen.getByText("Native and target language must be different.")).toBeInTheDocument();
    });
  });

  it("applies preset pair and swap controls in new space builder", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByLabelText("New space preset DE -> EN")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("New space preset DE -> EN"));
    expect(screen.getByLabelText("New space native language")).toHaveValue("de");
    expect(screen.getByLabelText("New space target language")).toHaveValue("en");

    fireEvent.click(screen.getByLabelText("New space swap languages"));
    expect(screen.getByLabelText("New space native language")).toHaveValue("en");
    expect(screen.getByLabelText("New space target language")).toHaveValue("de");
  });

  it("switches active learning space from manage list", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("listbox", { name: "Learning spaces" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("option", { name: /German \(de\) -> English \(en\) switch/i }));

    await waitFor(() => {
      expect(mocks.workspaceSwitch).toHaveBeenCalledWith({ workspace_id: 2 });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Learning space switched");
    });
  });

  it("resets all data with two-step confirmation", async () => {
    mocks.bootstrap.mockResolvedValue({
      user_id: 1,
      has_profile: false,
      needs_onboarding: true,
      next_step: "onboarding",
      owner_user_id: 1,
      active_workspace_id: null,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Start over" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Start over" }));
    fireEvent.change(screen.getByLabelText("Confirmation"), { target: { value: "RESET" } });
    fireEvent.click(screen.getByRole("button", { name: "Delete all data" }));

    await waitFor(() => {
      expect(mocks.appReset).toHaveBeenCalledWith({ confirmation: "RESET" });
      expect(mocks.navigate).toHaveBeenCalledWith("/", { replace: true });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "All learning data removed. Starting fresh.");
    });
  });

  it("exports backup as JSON", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Export" }));

    await waitFor(() => {
      expect(mocks.appBackupExport).toHaveBeenCalledTimes(1);
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Backup exported");
    });
  });

  it("imports backup file and restores after confirmation", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByLabelText("Import backup file")).toBeInTheDocument();
    });

    const payload = {
      version: 1,
      exported_at: "2026-03-06T00:00:00Z",
      snapshot: { users: [{ id: 1 }] },
    };
    const file = new File([JSON.stringify(payload)], "backup.json", { type: "application/json" });
    Object.defineProperty(file, "arrayBuffer", {
      value: vi.fn().mockResolvedValue(new TextEncoder().encode(JSON.stringify(payload)).buffer),
    });

    const importInput = screen.getByLabelText("Import backup file") as HTMLInputElement;
    Object.defineProperty(importInput, "files", {
      value: [file],
      configurable: true,
    });
    fireEvent.change(importInput);

    await waitFor(() => {
      expect(screen.getByLabelText("Type RESTORE to confirm")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Type RESTORE to confirm"), { target: { value: "RESTORE" } });
    fireEvent.click(screen.getByRole("button", { name: "Restore" }));

    await waitFor(() => {
      expect(mocks.appBackupRestore).toHaveBeenCalledWith({
        confirmation: "RESTORE",
        snapshot: { users: [{ id: 1 }] },
      });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Backup restored");
      expect(mocks.navigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("applies timeline filters", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByLabelText("Timeline skill filter")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Timeline skill filter"), { target: { value: "grammar" } });
    fireEvent.change(screen.getByLabelText("Timeline activity filter"), { target: { value: "chat" } });
    fireEvent.change(screen.getByLabelText("Timeline workspace filter"), { target: { value: "2" } });

    await waitFor(() => {
      expect(mocks.progressTimeline).toHaveBeenCalledWith(
        expect.objectContaining({
          user_id: 1,
          workspace_id: 2,
          skill: "grammar",
          activity_type: "chat",
        }),
      );
    });
  });
});
