import type {
  AppBackupExportResponse,
  AppBackupRestoreResponse,
  AppResetResponse,
  AppBootstrapResponse,
  PlacementAnswerResponse,
  PlacementFinishResponse,
  PlacementStartResponse,
  OpenAIDebugResponse,
  AIRuntimeStatus,
  OpenAIKeyStatus,
  UsageBudgetStatus,
  LanguageCapabilities,
  ProfileResponse,
  ChatMessageResponse,
  CoachErrorBankResponse,
  CoachNextActionsResponse,
  CoachReviewQueueResponse,
  CoachReactivationResponse,
  CoachDailyChallengeResponse,
  CoachTrajectoryResponse,
  CoachRoadmapResponse,
  OutcomePacksResponse,
  CoachSessionTodayResponse,
  CoachSessionProgressResponse,
  ChatStartResponse,
  ExercisesGenerateResponse,
  ExercisesGradeResponse,
  GrammarAnalyzeResponse,
  GrammarHistoryResponse,
  HomeworkItem,
  HomeworkListResponse,
  HomeworkDeleteResponse,
  HomeworkSubmitResponse,
  PlanTodayResponse,
  ProgressSkillMap,
  ProgressSkillTree,
  ProgressJournal,
  ProgressTimeline,
  WeeklyGoal,
  ProgressStreak,
  ProgressSummary,
  ProgressRewards,
  ProgressWeeklyReview,
  ProgressWeeklyCheckpoint,
  ProgressAchievements,
  ProgressReport,
  ScenarioSelectResponse,
  ScenarioScriptResponse,
  ScenarioTurnResponse,
  ScenariosResponse,
  CoachScenarioTracksResponse,
  TranslateResponse,
  TranslateVoiceResponse,
  VocabItem,
  VocabListResponse,
  VocabReviewNextResponse,
  VocabReviewSubmitResponse,
  VoiceMessageResponse,
  VoiceProgressResponse,
  WorkspaceListResponse,
  WorkspaceSwitchResponse,
  LearningWorkspace,
  WorkspaceDeleteResponse,
  WorkspaceOverviewResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 15000;

export class ApiError extends Error {
  status: number;
  requestId?: string;

  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.status = status;
    this.requestId = requestId;
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs: number = REQUEST_TIMEOUT_MS): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), timeoutMs);

  if (init?.signal) {
    init.signal.addEventListener("abort", () => timeoutController.abort(), { once: true });
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: isFormData
        ? init?.headers
        : {
            "Content-Type": "application/json",
            ...(init?.headers ?? {}),
          },
      ...init,
      signal: timeoutController.signal,
    });
  } catch (err) {
    if (timeoutController.signal.aborted) {
      throw new ApiError(`Request timeout after ${timeoutMs}ms`, 504);
    }
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(`Request timeout after ${timeoutMs}ms`, 504);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const text = await response.text();
    let detail = text;
    let requestId = response.headers.get("X-Request-ID") ?? undefined;
    try {
      const parsed = JSON.parse(text) as { detail?: string; error?: string; request_id?: string };
      detail = parsed.detail ?? parsed.error ?? text;
      requestId = parsed.request_id ?? requestId;
    } catch {
      // keep fallback text
    }
    throw new ApiError(detail, response.status, requestId);
  }
  return (await response.json()) as T;
}

export const api = {
  bootstrap: () => request<AppBootstrapResponse>("/app/bootstrap"),
  appReset: (payload: { confirmation: string }) =>
    request<AppResetResponse>("/app/reset", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  appBackupExport: () => request<AppBackupExportResponse>("/app/backup/export"),
  appBackupRestore: (payload: { confirmation: string; snapshot: Record<string, unknown> }) =>
    request<AppBackupRestoreResponse>("/app/backup/restore", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  workspacesList: () => request<WorkspaceListResponse>("/workspaces"),
  workspaceCreate: (payload: {
    native_lang: string;
    target_lang: string;
    goal?: string | null;
    make_active?: boolean;
  }) =>
    request<LearningWorkspace>("/workspaces", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  workspaceUpdate: (workspaceId: number, payload: { goal?: string | null }) =>
    request<LearningWorkspace>(`/workspaces/${encodeURIComponent(workspaceId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  workspaceSwitch: (payload: { workspace_id: number }) =>
    request<WorkspaceSwitchResponse>("/workspaces/switch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  workspaceActive: () => request<WorkspaceSwitchResponse>("/workspaces/active"),
  workspaceDelete: (workspaceId: number) =>
    request<WorkspaceDeleteResponse>(`/workspaces/${encodeURIComponent(workspaceId)}`, {
      method: "DELETE",
    }),
  workspacesOverview: () => request<WorkspaceOverviewResponse>("/workspaces/overview"),
  openaiKeyStatus: () => request<OpenAIKeyStatus>("/settings/openai-key"),
  openaiKeySet: (payload: { api_key: string }) =>
    request<OpenAIKeyStatus>("/settings/openai-key", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  usageBudgetStatus: (userId: number) =>
    request<UsageBudgetStatus>(`/settings/usage-budget?user_id=${encodeURIComponent(userId)}`),
  usageBudgetSet: (payload: {
    user_id: number;
    daily_token_cap: number;
    weekly_token_cap: number;
    warning_threshold: number;
  }) =>
    request<UsageBudgetStatus>("/settings/usage-budget", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  languageCapabilities: (nativeLang: string, targetLang: string) =>
    request<LanguageCapabilities>(
      `/settings/language-capabilities?native_lang=${encodeURIComponent(nativeLang)}&target_lang=${encodeURIComponent(
        targetLang,
      )}`,
    ),
  debugOpenai: () => request<OpenAIDebugResponse>("/debug/openai"),
  aiRuntimeStatus: (probe = false) => request<AIRuntimeStatus>(`/settings/ai-runtime?probe=${probe ? "true" : "false"}`),
  aiRuntimeSet: (payload: {
    llm_provider: "openai" | "local";
    asr_provider: "openai" | "local";
    tts_provider: "openai" | "local";
  }) =>
    request<AIRuntimeStatus>("/settings/ai-runtime", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  profileSetup: (payload: {
    user_id: number;
    native_lang: string;
    target_lang: string;
    level: string;
    goal?: string;
    preferences?: Record<string, unknown>;
  }) =>
    request<ProfileResponse>("/profile/setup", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  profileGet: (userId: number) => request<ProfileResponse>(`/profile?user_id=${encodeURIComponent(userId)}`),
  placementStart: (payload: { user_id: number; native_lang: string; target_lang: string }) =>
    request<PlacementStartResponse>("/profile/placement-test/start", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  placementAnswer: (payload: { session_id: number; answer: string }) =>
    request<PlacementAnswerResponse>("/profile/placement-test/answer", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  placementFinish: (payload: { session_id: number }) =>
    request<PlacementFinishResponse>("/profile/placement-test/finish", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  progressSummary: (userId: number) =>
    request<ProgressSummary>(`/progress/summary?user_id=${encodeURIComponent(userId)}`),
  planToday: (userId: number, timeBudgetMinutes = 15) =>
    request<PlanTodayResponse>(
      `/plan/today?user_id=${encodeURIComponent(userId)}&time_budget_minutes=${encodeURIComponent(timeBudgetMinutes)}`,
    ),
  coachSessionToday: (userId: number, timeBudgetMinutes = 15) =>
    request<CoachSessionTodayResponse>(
      `/coach/session/today?user_id=${encodeURIComponent(userId)}&time_budget_minutes=${encodeURIComponent(timeBudgetMinutes)}`,
    ),
  coachSessionProgress: (userId: number, timeBudgetMinutes = 15) =>
    request<CoachSessionProgressResponse>(
      `/coach/session/progress?user_id=${encodeURIComponent(userId)}&time_budget_minutes=${encodeURIComponent(timeBudgetMinutes)}`,
    ),
  coachSessionProgressUpsert: (payload: {
    user_id: number;
    step_id: string;
    status: "pending" | "in_progress" | "completed";
    time_budget_minutes?: number;
  }) =>
    request<CoachSessionProgressResponse>("/coach/session/progress", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  coachNextActions: (userId: number) =>
    request<CoachNextActionsResponse>(`/coach/next-actions?user_id=${encodeURIComponent(userId)}`),
  coachReviewQueue: (userId: number) =>
    request<CoachReviewQueueResponse>(`/coach/review-queue?user_id=${encodeURIComponent(userId)}`),
  coachErrorBank: (userId: number, limit = 5) =>
    request<CoachErrorBankResponse>(
      `/coach/error-bank?user_id=${encodeURIComponent(userId)}&limit=${encodeURIComponent(limit)}`,
    ),
  coachReactivation: (userId: number, availableMinutes = 15) =>
    request<CoachReactivationResponse>(
      `/coach/reactivation?user_id=${encodeURIComponent(userId)}&available_minutes=${encodeURIComponent(availableMinutes)}`,
    ),
  coachDailyChallenge: (userId: number) =>
    request<CoachDailyChallengeResponse>(`/coach/daily-challenge?user_id=${encodeURIComponent(userId)}`),
  coachTrajectory: (userId: number, horizonDays = 30) =>
    request<CoachTrajectoryResponse>(
      `/coach/trajectory?user_id=${encodeURIComponent(userId)}&horizon_days=${encodeURIComponent(horizonDays)}`,
    ),
  coachRoadmap: (userId: number) =>
    request<CoachRoadmapResponse>(`/coach/roadmap?user_id=${encodeURIComponent(userId)}`),
  coachOutcomePacks: (userId: number) =>
    request<OutcomePacksResponse>(`/coach/outcome-packs?user_id=${encodeURIComponent(userId)}`),
  scenarios: (userId?: number) =>
    request<ScenariosResponse>(
      `/scenarios${typeof userId === "number" ? `?user_id=${encodeURIComponent(userId)}` : ""}`,
    ),
  coachScenarioTracks: (userId: number, goal?: string) =>
    request<CoachScenarioTracksResponse>(
      `/coach/scenario-tracks?user_id=${encodeURIComponent(userId)}${
        goal ? `&goal=${encodeURIComponent(goal)}` : ""
      }`,
    ),
  selectScenario: (payload: { user_id: number; scenario_id: string }) =>
    request<ScenarioSelectResponse>("/scenarios/select", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  scenarioScript: (scenarioId: string, userId?: number) =>
    request<ScenarioScriptResponse>(
      `/scenarios/script?scenario_id=${encodeURIComponent(scenarioId)}${
        userId ? `&user_id=${encodeURIComponent(userId)}` : ""
      }`,
    ),
  scenarioTurn: (payload: { user_id: number; scenario_id: string; step_id: string; user_text: string }) =>
    request<ScenarioTurnResponse>("/scenarios/turn", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  translate: (payload: {
    user_id?: number;
    text: string;
    source_lang: string;
    target_lang: string;
    voice?: boolean;
  }) =>
    request<TranslateResponse>("/translate", {
      method: "POST",
      body: JSON.stringify(payload),
    }, 90000),
  translateVoice: (payload: {
    file: File;
    source_lang: string;
    target_lang: string;
    language_hint?: string;
  }) => {
    const formData = new FormData();
    formData.set("file", payload.file);
    formData.set("source_lang", payload.source_lang);
    formData.set("target_lang", payload.target_lang);
    formData.set("language_hint", payload.language_hint ?? "auto");
    return request<TranslateVoiceResponse>("/translate/voice", {
      method: "POST",
      body: formData,
    }, 180000);
  },
  grammarAnalyze: (payload: { user_id: number; text: string; target_lang: string }) =>
    request<GrammarAnalyzeResponse>("/grammar/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  grammarHistory: (userId: number, limit = 25) =>
    request<GrammarHistoryResponse>(
      `/grammar/history?user_id=${encodeURIComponent(userId)}&limit=${encodeURIComponent(limit)}`,
    ),
  generateExercises: (payload: {
    user_id: number;
    exercise_type: string;
    topic: string;
    count: number;
  }) =>
    request<ExercisesGenerateResponse>("/exercises/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  gradeExercises: (payload: { answers: Record<string, string>; expected: Record<string, string> }) =>
    request<ExercisesGradeResponse>("/exercises/grade", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  chatStart: (payload: { user_id: number; mode?: string }) =>
    request<ChatStartResponse>("/chat/start", {
      method: "POST",
      body: JSON.stringify({ user_id: payload.user_id, mode: payload.mode ?? "chat" }),
    }),
  chatMessage: (payload: { session_id: number; text: string }) =>
    request<ChatMessageResponse>("/chat/message", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  chatEnd: (payload: { session_id: number }) =>
    request<{ session_id: number; status: string }>("/chat/end", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  voiceMessage: (payload: {
    file: File;
    user_id: number;
    target_lang: string;
    language_hint?: string;
    voice_name?: string;
  }) => {
    const formData = new FormData();
    formData.set("file", payload.file);
    formData.set("user_id", String(payload.user_id));
    formData.set("target_lang", payload.target_lang);
    formData.set("language_hint", payload.language_hint ?? payload.target_lang);
    formData.set("voice_name", payload.voice_name ?? "alloy");
    return request<VoiceMessageResponse>("/voice/message", {
      method: "POST",
      body: formData,
    });
  },
  voiceProgress: (userId: number) =>
    request<VoiceProgressResponse>(`/voice/progress?user_id=${encodeURIComponent(userId)}`),
  vocabList: (userId: number) => request<VocabListResponse>(`/vocab?user_id=${encodeURIComponent(userId)}`),
  vocabAdd: (payload: { user_id: number; word: string; translation: string; example?: string }) =>
    request<VocabItem>("/vocab/add", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  vocabReviewNext: (payload: { user_id: number }) =>
    request<VocabReviewNextResponse>("/vocab/review/next", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  vocabReviewSubmit: (payload: { user_id: number; vocab_item_id: number; rating: "again" | "hard" | "good" | "easy" }) =>
    request<VocabReviewSubmitResponse>("/vocab/review/submit", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  homeworkCreate: (payload: {
    user_id: number;
    title: string;
    tasks: Array<Record<string, unknown>>;
    due_at?: string;
  }) =>
    request<HomeworkItem>("/homework/create", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  homeworkList: (userId: number) =>
    request<HomeworkListResponse>(`/homework?user_id=${encodeURIComponent(userId)}`),
  homeworkUpdate: (
    homeworkId: number,
    payload: {
      title: string;
      tasks: Array<Record<string, unknown>>;
      due_at?: string | null;
      status: string;
    },
  ) =>
    request<HomeworkItem>(`/homework/${encodeURIComponent(homeworkId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  homeworkDelete: (homeworkId: number) =>
    request<HomeworkDeleteResponse>(`/homework/${encodeURIComponent(homeworkId)}`, {
      method: "DELETE",
    }),
  homeworkSubmit: (payload: { homework_id: number; answers: Record<string, string> }) =>
    request<HomeworkSubmitResponse>("/homework/submit", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  progressSkillMap: (userId: number) =>
    request<ProgressSkillMap>(`/progress/skill-map?user_id=${encodeURIComponent(userId)}`),
  progressSkillTree: (userId: number) =>
    request<ProgressSkillTree>(`/progress/skill-tree?user_id=${encodeURIComponent(userId)}`),
  progressStreak: (userId: number) =>
    request<ProgressStreak>(`/progress/streak?user_id=${encodeURIComponent(userId)}`),
  progressJournal: (userId: number) =>
    request<ProgressJournal>(`/progress/journal?user_id=${encodeURIComponent(userId)}`),
  progressTimeline: (payload: {
    user_id: number;
    workspace_id?: number;
    skill?: string;
    activity_type?: string;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    params.set("user_id", String(payload.user_id));
    if (typeof payload.workspace_id === "number") params.set("workspace_id", String(payload.workspace_id));
    if (payload.skill) params.set("skill", payload.skill);
    if (payload.activity_type) params.set("activity_type", payload.activity_type);
    if (typeof payload.limit === "number") params.set("limit", String(payload.limit));
    return request<ProgressTimeline>(`/progress/timeline?${params.toString()}`);
  },
  progressWeeklyGoal: (userId: number) =>
    request<WeeklyGoal>(`/progress/weekly-goal?user_id=${encodeURIComponent(userId)}`),
  progressWeeklyGoalSet: (payload: { user_id: number; target_minutes: number }) =>
    request<WeeklyGoal>("/progress/weekly-goal", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  progressRewards: (userId: number) =>
    request<ProgressRewards>(`/progress/rewards?user_id=${encodeURIComponent(userId)}`),
  progressRewardsClaim: (payload: { user_id: number; reward_id: string }) =>
    request<ProgressRewards>("/progress/rewards/claim", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  progressWeeklyReview: (userId: number) =>
    request<ProgressWeeklyReview>(`/progress/weekly-review?user_id=${encodeURIComponent(userId)}`),
  progressWeeklyCheckpoint: (userId: number, windowDays = 7) =>
    request<ProgressWeeklyCheckpoint>(
      `/progress/weekly-checkpoint?user_id=${encodeURIComponent(userId)}&window_days=${encodeURIComponent(windowDays)}`,
    ),
  progressAchievements: (userId: number) =>
    request<ProgressAchievements>(`/progress/achievements?user_id=${encodeURIComponent(userId)}`),
  progressReport: (userId: number, periodDays = 30) =>
    request<ProgressReport>(
      `/progress/report?user_id=${encodeURIComponent(userId)}&period_days=${encodeURIComponent(periodDays)}`,
    ),
};
