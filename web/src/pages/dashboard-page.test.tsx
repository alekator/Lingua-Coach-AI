import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent } from "@testing-library/react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DashboardPage } from "./dashboard-page";

const routerFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

const mocks = vi.hoisted(() => ({
  progressSummary: vi.fn(),
  progressWeeklyGoal: vi.fn(),
  progressWeeklyGoalSet: vi.fn(),
  coachNextActions: vi.fn(),
  coachReactivation: vi.fn(),
  coachDailyChallenge: vi.fn(),
  planToday: vi.fn(),
  progressRewards: vi.fn(),
  progressRewardsClaim: vi.fn(),
  progressWeeklyReview: vi.fn(),
  workspacesOverview: vi.fn(),
  workspaceSwitch: vi.fn(),
  bootstrap: vi.fn(),
  pushToast: vi.fn(),
  setDailyMinutes: vi.fn(),
  setBootstrapState: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    progressSummary: mocks.progressSummary,
    progressWeeklyGoal: mocks.progressWeeklyGoal,
    progressWeeklyGoalSet: mocks.progressWeeklyGoalSet,
    coachNextActions: mocks.coachNextActions,
    coachReactivation: mocks.coachReactivation,
    coachDailyChallenge: mocks.coachDailyChallenge,
    planToday: mocks.planToday,
    progressRewards: mocks.progressRewards,
    progressRewardsClaim: mocks.progressRewardsClaim,
    progressWeeklyReview: mocks.progressWeeklyReview,
    workspacesOverview: mocks.workspacesOverview,
    workspaceSwitch: mocks.workspaceSwitch,
    bootstrap: mocks.bootstrap,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (
    selector: (state: {
      userId: number;
      activeWorkspaceId: number;
      setDailyMinutes: (minutes: number) => void;
      setBootstrapState: typeof mocks.setBootstrapState;
    }) => unknown,
  ) =>
    selector({
      userId: 1,
      activeWorkspaceId: 1,
      setDailyMinutes: mocks.setDailyMinutes,
      setBootstrapState: mocks.setBootstrapState,
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
      <MemoryRouter future={routerFuture}>
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
    mocks.coachNextActions.mockResolvedValue({
      user_id: 1,
      items: [
        {
          id: "weekly-goal",
          title: "Complete 96 more weekly minutes",
          reason: "Weekly target not completed yet.",
          route: "/app/session",
          priority: 1,
        },
      ],
    });
    mocks.coachReactivation.mockResolvedValue({
      user_id: 1,
      eligible: true,
      gap_days: 3,
      weak_topic: "grammar",
      title: "Easy return plan after 3 day break",
      tasks: [
        "2 min: quick warmup in grammar with one simple sentence.",
        "2 min: one short coach chat turn and apply one correction.",
        "1 min: close with one success line to lock momentum.",
      ],
      cta_route: "/app/session",
      note: "Keep it light today. The goal is to restart momentum, not intensity.",
    });
    mocks.coachDailyChallenge.mockResolvedValue({
      user_id: 1,
      title: "Daily Challenge: One Clear Step",
      reason: "Fast progress for your travel goal with minimal friction.",
      task: "Write one short message focused on grammar, then apply one correction.",
      route: "/app/chat",
      estimated_minutes: 5,
    });
    mocks.progressRewards.mockResolvedValue({
      user_id: 1,
      total_xp: 30,
      claimed_count: 1,
      items: [
        {
          id: "streak_3",
          title: "3-Day Streak",
          description: "You studied 3 days in a row.",
          requirement: "Reach a 3-day streak",
          xp_points: 30,
          status: "claimed",
        },
        {
          id: "weekly_goal_complete",
          title: "Weekly Goal Complete",
          description: "You completed your weekly minutes target.",
          requirement: "Complete weekly goal",
          xp_points: 60,
          status: "available",
        },
      ],
    });
    mocks.progressRewardsClaim.mockResolvedValue({
      user_id: 1,
      total_xp: 90,
      claimed_count: 2,
      items: [],
    });
    mocks.progressWeeklyReview.mockResolvedValue({
      user_id: 1,
      weekly_minutes: 24,
      weekly_sessions: 3,
      weekly_goal_target_minutes: 120,
      weekly_goal_completed: false,
      streak_days: 3,
      strongest_skill: "vocab",
      weakest_skill: "grammar",
      top_weak_area: "grammar",
      wins: ["3 sessions completed this week.", "24 active learning minutes logged."],
      next_focus: "Keep momentum with one short drill in grammar and one coach chat turn.",
    });
    mocks.workspacesOverview.mockResolvedValue({
      owner_user_id: 1,
      items: [
        {
          workspace_id: 1,
          native_lang: "ru",
          target_lang: "en",
          goal: "travel",
          is_active: true,
          has_profile: true,
          streak_days: 3,
          minutes_practiced: 24,
          words_learned: 8,
          last_activity_at: "2026-03-06T10:00:00Z",
        },
        {
          workspace_id: 2,
          native_lang: "de",
          target_lang: "en",
          goal: "job",
          is_active: false,
          has_profile: false,
          streak_days: 0,
          minutes_practiced: 0,
          words_learned: 0,
          last_activity_at: null,
        },
      ],
    });
    mocks.workspaceSwitch.mockResolvedValue({ active_workspace_id: 2, active_user_id: 2 });
    mocks.bootstrap.mockResolvedValue({
      user_id: 2,
      has_profile: false,
      needs_onboarding: true,
      next_step: "onboarding",
      owner_user_id: 1,
      active_workspace_id: 2,
      active_workspace_native_lang: "de",
      active_workspace_target_lang: "en",
      active_workspace_goal: "job",
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
      expect(screen.getByText("Coach Next Actions")).toBeInTheDocument();
      expect(screen.getAllByText("Complete 96 more weekly minutes").length).toBeGreaterThan(0);
      expect(screen.getByText("Today one step:")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Do next best action" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Start 5-minute mode" })).toBeInTheDocument();
      expect(screen.getByText("Easy Return Plan")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Start easy return (5 min)" })).toBeInTheDocument();
      expect(screen.getByText("Rewards")).toBeInTheDocument();
      expect(screen.getByText("XP: 30 | Claimed: 1")).toBeInTheDocument();
      expect(screen.getByText("Weekly Review")).toBeInTheDocument();
      expect(screen.getByText("Skills: strongest vocab, weakest grammar")).toBeInTheDocument();
      expect(screen.getByText("Daily Challenge")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Start daily challenge" })).toBeInTheDocument();
      expect(screen.getByText("Your Learning Spaces")).toBeInTheDocument();
      expect(screen.getByText("Needs onboarding to unlock full coach flow.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Switch and open" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Save weekly goal" }));
    await waitFor(() => {
      expect(mocks.progressWeeklyGoalSet).toHaveBeenCalledWith({ user_id: 1, target_minutes: 120 });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Weekly goal updated");
    });

    fireEvent.click(screen.getByRole("button", { name: "Start 5-minute mode" }));
    await waitFor(() => {
      expect(mocks.setDailyMinutes).toHaveBeenCalledWith(5);
      expect(mocks.pushToast).toHaveBeenCalledWith("info", "5-minute mode enabled for today");
      expect(screen.getByText(/Reactivation:/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Start easy return (5 min)" }));
    await waitFor(() => {
      expect(mocks.setDailyMinutes).toHaveBeenCalledWith(5);
    });

    fireEvent.click(screen.getByRole("button", { name: "Claim reward" }));
    await waitFor(() => {
      expect(mocks.progressRewardsClaim).toHaveBeenCalledWith({ user_id: 1, reward_id: "weekly_goal_complete" });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Reward claimed");
    });

    fireEvent.click(screen.getByRole("button", { name: "Switch and open" }));
    await waitFor(() => {
      expect(mocks.workspaceSwitch).toHaveBeenCalledWith({ workspace_id: 2 });
      expect(mocks.setBootstrapState).toHaveBeenCalledWith(
        expect.objectContaining({
          userId: 2,
          hasProfile: false,
          activeWorkspaceId: 2,
        }),
      );
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Switched learning space");
    });
  });
});
