import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import { getWorkspaceResumeRoute } from "../lib/workspace-routes";
import { syncWorkspaceContext } from "../lib/workspace-context";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const userId = useAppStore((s) => s.userId) ?? 1;
  const setBootstrapState = useAppStore((s) => s.setBootstrapState);
  const activeWorkspaceId = useAppStore((s) => s.activeWorkspaceId);
  const dailyMinutes = useAppStore((s) => s.dailyMinutes);
  const setDailyMinutes = useAppStore((s) => s.setDailyMinutes);
  const pushToast = useToastStore((s) => s.push);
  const [goalMinutes, setGoalMinutes] = useState(120);
  const [goalError, setGoalError] = useState("");
  const [showInsights, setShowInsights] = useState(false);
  const summary = useQuery({
    queryKey: ["summary", userId],
    queryFn: () => api.progressSummary(userId),
  });
  const weeklyGoal = useQuery({
    queryKey: ["weekly-goal", userId],
    queryFn: () => api.progressWeeklyGoal(userId),
  });
  const plan = useQuery({
    queryKey: ["plan-today", userId, dailyMinutes],
    queryFn: () => api.planToday(userId, dailyMinutes),
  });
  const nextActions = useQuery({
    queryKey: ["coach-next-actions", userId],
    queryFn: () => api.coachNextActions(userId),
  });
  const reviewQueue = useQuery({
    queryKey: ["coach-review-queue", userId],
    queryFn: () => api.coachReviewQueue(userId),
  });
  const reactivation = useQuery({
    queryKey: ["coach-reactivation", userId, dailyMinutes],
    queryFn: () => api.coachReactivation(userId, dailyMinutes),
  });
  const dailyChallenge = useQuery({
    queryKey: ["coach-daily-challenge", userId],
    queryFn: () => api.coachDailyChallenge(userId),
  });
  const rewards = useQuery({
    queryKey: ["progress-rewards", userId],
    queryFn: () => api.progressRewards(userId),
  });
  const weeklyReview = useQuery({
    queryKey: ["progress-weekly-review", userId],
    queryFn: () => api.progressWeeklyReview(userId),
  });
  const weeklyCheckpoint = useQuery({
    queryKey: ["progress-weekly-checkpoint", userId],
    queryFn: () => api.progressWeeklyCheckpoint(userId, 7),
  });
  const spacesOverview = useQuery({
    queryKey: ["workspaces-overview"],
    queryFn: api.workspacesOverview,
  });

  async function onSaveGoal() {
    try {
      await api.progressWeeklyGoalSet({ user_id: userId, target_minutes: goalMinutes });
      setGoalError("");
      pushToast("success", "Weekly goal updated");
      await weeklyGoal.refetch();
    } catch (err) {
      const msg = getErrorMessage(err);
      setGoalError(msg);
      pushToast("error", msg);
    }
  }

  async function onClaimReward(rewardId: string) {
    try {
      await api.progressRewardsClaim({ user_id: userId, reward_id: rewardId });
      pushToast("success", "Reward claimed");
      await rewards.refetch();
    } catch (err) {
      pushToast("error", getErrorMessage(err));
    }
  }

  async function onSwitchSpace(workspaceId: number) {
    try {
      await api.workspaceSwitch({ workspace_id: workspaceId });
      const bootstrap = await syncWorkspaceContext(queryClient, setBootstrapState);
      if (bootstrap.needs_onboarding) {
        pushToast("info", "This learning space is new. Complete placement to start.");
        navigate("/", { replace: true });
        return;
      }
      pushToast("success", "Switched learning space");
      if (bootstrap.active_workspace_id) {
        navigate(getWorkspaceResumeRoute(bootstrap.active_workspace_id) ?? "/app", { replace: true });
      } else {
        navigate("/app", { replace: true });
      }
    } catch (err) {
      pushToast("error", getErrorMessage(err));
    }
  }

  function startQuickMode(route = "/app/session", minutes = 5) {
    const safeMinutes = Math.max(5, Math.min(60, minutes));
    setDailyMinutes(safeMinutes);
    pushToast("info", `${safeMinutes}-minute mode enabled for today`);
    navigate(route);
  }

  function runNextBestAction() {
    if (!nextBestAction) return;
    const quickMinutes = nextBestAction.quick_mode_minutes;
    if (typeof quickMinutes === "number" && quickMinutes >= 5) {
      setDailyMinutes(quickMinutes);
      pushToast("info", `Mode set to ${quickMinutes} minutes for this action`);
    }
    navigate(nextBestAction.route);
  }

  const nextBestAction = nextActions.data?.items?.[0] ?? null;
  const todayOneStepTitle = nextBestAction?.title ?? plan.data?.tasks?.[0] ?? "Start your guided daily session";
  const todayOneStepReason =
    nextBestAction?.reason ??
    (plan.data ? `Focus today: ${plan.data.focus.join(", ")}.` : "One clear action to keep momentum.");
  const todayOneStepMinutes =
    (typeof nextBestAction?.quick_mode_minutes === "number" ? nextBestAction.quick_mode_minutes : null) ??
    plan.data?.time_budget_minutes ??
    dailyMinutes;
  const todayOneStepRoute = nextBestAction?.route ?? "/app/session";
  const reactivationMsg =
    reactivation.data && reactivation.data.eligible
      ? `You had a ${reactivation.data.gap_days}-day pause. ${reactivation.data.note}`
      : null;
  const workspaceItems = Array.isArray(spacesOverview.data?.items) ? spacesOverview.data.items : [];

  return (
    <section className="panel">
      <h2>Dashboard</h2>
      <p>Your coaching loop for today. Follow the plan, then track improvement in Profile.</p>
      <article className="panel stack">
        <h3>Today Focus</h3>
        <p>
          <strong>One next step:</strong> {todayOneStepTitle}
        </p>
        <p>{todayOneStepReason}</p>
        <p>Recommended mode: {Math.max(5, Math.min(60, todayOneStepMinutes))} min</p>
        {reactivationMsg && <p>Reactivation: {reactivationMsg}</p>}
        <button
          type="button"
          className="cta-primary"
          onClick={() => {
            if (nextBestAction) {
              runNextBestAction();
              return;
            }
            startQuickMode(todayOneStepRoute, todayOneStepMinutes);
          }}
        >
          Start today one step
        </button>
        <button type="button" className="cta-secondary" onClick={() => setShowInsights((prev) => !prev)}>
          {showInsights ? "Hide full insights" : "Show full insights"}
        </button>
      </article>
      {summary.isPending && <LoadingState text="Loading progress..." />}
      {summary.isError && <ErrorState text="Failed to load progress summary." />}
      {summary.isSuccess && summary.data.minutes_practiced === 0 && (
        <EmptyState text="No study activity yet. Start chat, voice, or exercises." />
      )}
      {summary.isSuccess && (
        <div className="grid">
          <article>
            <h3>Streak</h3>
            <p>{summary.data.streak_days} days</p>
          </article>
          <article>
            <h3>Practice Time</h3>
            <p>{summary.data.minutes_practiced} minutes</p>
          </article>
          <article>
            <h3>Words Learned</h3>
            <p>{summary.data.words_learned}</p>
          </article>
        </div>
      )}
      {spacesOverview.isPending && <LoadingState text="Loading learning spaces overview..." />}
      {spacesOverview.isError && <ErrorState text="Failed to load learning spaces overview." />}
      {spacesOverview.isSuccess && workspaceItems.length > 0 && (
        <article className="panel stack">
          <h3>Your Learning Spaces</h3>
          <p>Each pair is an isolated coach space with separate progress and history.</p>
          {workspaceItems.map((item) => (
            <div key={item.workspace_id} className="panel stack">
              <p>
                <strong>
                  {item.native_lang} {"->"} {item.target_lang}
                </strong>{" "}
                {item.is_active ? "(active)" : ""}
              </p>
              <p>Goal: {item.goal || "not set yet"}</p>
              <p>
                Streak: {item.streak_days} | Minutes: {item.minutes_practiced} | Words: {item.words_learned}
              </p>
              {!item.has_profile && <p>Needs onboarding to unlock full coach flow.</p>}
              {item.workspace_id !== activeWorkspaceId && (
                <button type="button" onClick={() => onSwitchSpace(item.workspace_id)}>
                  Switch and open
                </button>
              )}
            </div>
          ))}
        </article>
      )}
      {showInsights && weeklyGoal.isPending && <LoadingState text="Loading weekly goal..." />}
      {showInsights && weeklyGoal.isError && <ErrorState text="Failed to load weekly goal." />}
      {showInsights && weeklyGoal.isSuccess && (
        <article className="panel stack">
          <h3>Weekly Goal Tracker</h3>
          <p>
            Progress: {weeklyGoal.data.completed_minutes}/{weeklyGoal.data.target_minutes} min (
            {weeklyGoal.data.completion_percent}%)
          </p>
          <p>
            {weeklyGoal.data.is_completed
              ? "Goal completed for this week. Keep momentum."
              : `Remaining: ${weeklyGoal.data.remaining_minutes} min`}
          </p>
          <label>
            Set weekly goal (minutes)
            <input
              type="number"
              min={30}
              max={2000}
              value={goalMinutes}
              onChange={(e) => setGoalMinutes(Number(e.target.value || 120))}
            />
          </label>
          <button type="button" onClick={onSaveGoal}>
            Save weekly goal
          </button>
          {goalError && <ErrorState text={goalError} />}
        </article>
      )}
      {showInsights && nextActions.isPending && <LoadingState text="Loading coach next actions..." />}
      {showInsights && nextActions.isError && <ErrorState text="Failed to load coach next actions." />}
      {showInsights && nextActions.isSuccess && (
        <article className="panel stack">
          <h3>Coach Next Actions</h3>
          {nextBestAction && (
            <div className="panel stack">
              <p>
                <strong>Today one step:</strong> {nextBestAction.title}
              </p>
              <p>{nextBestAction.reason}</p>
              <button type="button" onClick={runNextBestAction}>
                Do next best action
              </button>
              <button type="button" onClick={() => startQuickMode("/app/session", 5)}>
                Start 5-minute mode
              </button>
              {reactivationMsg && <p>Reactivation: {reactivationMsg}</p>}
            </div>
          )}
          {nextActions.data.items.map((item) => (
            <div key={item.id} className="panel stack">
              <p>
                <strong>{item.title}</strong>
              </p>
              <p>{item.reason}</p>
              <Link to={item.route}>
                <button type="button">Open action</button>
              </Link>
            </div>
          ))}
        </article>
      )}
      {showInsights && reviewQueue.isPending && <LoadingState text="Loading review queue..." />}
      {showInsights && reviewQueue.isError && <ErrorState text="Failed to load review queue." />}
      {showInsights && reviewQueue.isSuccess && (
        <article className="panel stack">
          <h3>Unified Review Queue</h3>
          <p>One place for spaced review of vocabulary, recurring errors, grammar and pronunciation.</p>
          {reviewQueue.data.items.map((item) => (
            <div key={item.id} className="panel stack">
              <p>
                <strong>{item.title}</strong> ({item.estimated_minutes} min)
              </p>
              <p>{item.reason}</p>
              <Link to={item.route}>
                <button type="button">Open review</button>
              </Link>
            </div>
          ))}
        </article>
      )}
      {showInsights && reactivation.isSuccess && reactivation.data.eligible && (
        <article className="panel stack">
          <h3>Easy Return Plan</h3>
          <p>{reactivation.data.title}</p>
          {reactivation.data.weak_topic && <p>Focus area: {reactivation.data.weak_topic}</p>}
          {reactivation.data.tasks.map((task) => (
            <p key={task}>- {task}</p>
          ))}
          <button
            type="button"
            onClick={() =>
              startQuickMode(
                reactivation.data.cta_route || "/app/session",
                reactivation.data.recommended_minutes || 5,
              )
            }
          >
            Start easy return ({reactivation.data.recommended_minutes} min)
          </button>
        </article>
      )}
      {showInsights && dailyChallenge.isPending && <LoadingState text="Loading daily challenge..." />}
      {showInsights && dailyChallenge.isError && <ErrorState text="Failed to load daily challenge." />}
      {showInsights && dailyChallenge.isSuccess && (
        <article className="panel stack">
          <h3>Daily Challenge</h3>
          <p>
            <strong>{dailyChallenge.data.title}</strong> ({dailyChallenge.data.estimated_minutes} min)
          </p>
          <p>{dailyChallenge.data.reason}</p>
          <p>{dailyChallenge.data.task}</p>
          <Link to={dailyChallenge.data.route}>
            <button type="button">Start daily challenge</button>
          </Link>
        </article>
      )}
      {showInsights && rewards.isPending && <LoadingState text="Loading rewards..." />}
      {showInsights && rewards.isError && <ErrorState text="Failed to load rewards." />}
      {showInsights && rewards.isSuccess && (
        <article className="panel stack">
          <h3>Rewards</h3>
          <p>
            XP: {rewards.data.total_xp} | Claimed: {rewards.data.claimed_count}
          </p>
          {rewards.data.items.map((item) => (
            <div key={item.id} className="panel stack">
              <p>
                <strong>{item.title}</strong> ({item.xp_points} XP)
              </p>
              <p>{item.description}</p>
              <p>Requirement: {item.requirement}</p>
              {item.status === "available" && (
                <button type="button" onClick={() => onClaimReward(item.id)}>
                  Claim reward
                </button>
              )}
              {item.status === "claimed" && <p>Status: claimed</p>}
              {item.status === "locked" && <p>Status: locked</p>}
            </div>
          ))}
        </article>
      )}
      {showInsights && weeklyReview.isPending && <LoadingState text="Loading weekly review..." />}
      {showInsights && weeklyReview.isError && <ErrorState text="Failed to load weekly review." />}
      {showInsights && weeklyReview.isSuccess && (
        <article className="panel stack">
          <h3>Weekly Review</h3>
          <p>
            Sessions: {weeklyReview.data.weekly_sessions} | Minutes: {weeklyReview.data.weekly_minutes}
          </p>
          <p>
            Goal: {weeklyReview.data.weekly_goal_target_minutes} min{" "}
            {weeklyReview.data.weekly_goal_completed ? "(completed)" : "(in progress)"}
          </p>
          <p>
            Skills: strongest {weeklyReview.data.strongest_skill}, weakest {weeklyReview.data.weakest_skill}
          </p>
          {weeklyReview.data.top_weak_area && <p>Most frequent weak area: {weeklyReview.data.top_weak_area}</p>}
          {weeklyReview.data.wins.map((win) => (
            <p key={win}>- {win}</p>
          ))}
          <p>Next focus: {weeklyReview.data.next_focus}</p>
        </article>
      )}
      {showInsights && weeklyCheckpoint.isPending && <LoadingState text="Loading weekly checkpoint..." />}
      {showInsights && weeklyCheckpoint.isError && <ErrorState text="Failed to load weekly checkpoint." />}
      {showInsights && weeklyCheckpoint.isSuccess && (
        <article className="panel stack">
          <h3>Weekly Checkpoint (Before/After)</h3>
          <p>
            Avg skill: {weeklyCheckpoint.data.baseline_avg_skill} {"->"} {weeklyCheckpoint.data.current_avg_skill}
          </p>
          <p>
            Delta: {weeklyCheckpoint.data.delta_points} points ({weeklyCheckpoint.data.delta_percent}%)
          </p>
          <p>
            Top gain: {weeklyCheckpoint.data.top_gain_skill} ({weeklyCheckpoint.data.top_gain_points} points)
          </p>
          <p>Status: {weeklyCheckpoint.data.measurable_growth ? "measurable growth" : "no measurable growth yet"}</p>
          <p>{weeklyCheckpoint.data.summary}</p>
        </article>
      )}
      {showInsights && plan.isPending && <LoadingState text="Generating today plan..." />}
      {showInsights && plan.isError && <ErrorState text="Failed to load daily plan." />}
      {showInsights && plan.isSuccess && (
        <article className="panel">
          <h3>Today Coaching Plan ({plan.data.time_budget_minutes} min)</h3>
          <p>Current habit mode: {dailyMinutes}-minute loop.</p>
          <p>Focus pillars: {plan.data.focus.join(", ")}</p>
          {plan.data.adaptation_notes.map((note) => (
            <p key={note}>Adaptation: {note}</p>
          ))}
          {plan.data.tasks.map((task) => (
            <p key={task}>- {task}</p>
          ))}
          <Link to="/app/session">
            <button type="button">Start today session</button>
          </Link>
        </article>
      )}
    </section>
  );
}
