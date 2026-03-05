import type {
  AppBootstrapResponse,
  PlacementAnswerResponse,
  PlacementFinishResponse,
  PlacementStartResponse,
  OpenAIDebugResponse,
  OpenAIKeyStatus,
  ProfileResponse,
  ChatMessageResponse,
  CoachNextActionsResponse,
  CoachSessionTodayResponse,
  ChatStartResponse,
  ExercisesGenerateResponse,
  ExercisesGradeResponse,
  GrammarAnalyzeResponse,
  HomeworkItem,
  HomeworkListResponse,
  HomeworkSubmitResponse,
  PlanTodayResponse,
  ProgressSkillMap,
  ProgressJournal,
  WeeklyGoal,
  ProgressStreak,
  ProgressSummary,
  ScenarioSelectResponse,
  ScenarioScriptResponse,
  ScenarioTurnResponse,
  ScenariosResponse,
  TranslateResponse,
  TranslateVoiceResponse,
  VocabItem,
  VocabListResponse,
  VocabReviewNextResponse,
  VocabReviewSubmitResponse,
  VoiceMessageResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  requestId?: string;

  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.status = status;
    this.requestId = requestId;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    headers: isFormData
      ? init?.headers
      : {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
    ...init,
  });
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
  openaiKeyStatus: () => request<OpenAIKeyStatus>("/settings/openai-key"),
  openaiKeySet: (payload: { api_key: string }) =>
    request<OpenAIKeyStatus>("/settings/openai-key", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  debugOpenai: () => request<OpenAIDebugResponse>("/debug/openai"),
  profileSetup: (payload: {
    user_id: number;
    native_lang: string;
    target_lang: string;
    level: string;
    goal?: string;
    preferences?: Record<string, unknown>;
  }) =>
    request("/profile/setup", {
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
  coachNextActions: (userId: number) =>
    request<CoachNextActionsResponse>(`/coach/next-actions?user_id=${encodeURIComponent(userId)}`),
  scenarios: () => request<ScenariosResponse>("/scenarios"),
  selectScenario: (payload: { user_id: number; scenario_id: string }) =>
    request<ScenarioSelectResponse>("/scenarios/select", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  scenarioScript: (scenarioId: string) =>
    request<ScenarioScriptResponse>(`/scenarios/script?scenario_id=${encodeURIComponent(scenarioId)}`),
  scenarioTurn: (payload: { user_id: number; scenario_id: string; step_id: string; user_text: string }) =>
    request<ScenarioTurnResponse>("/scenarios/turn", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  translate: (payload: { text: string; source_lang: string; target_lang: string; voice?: boolean }) =>
    request<TranslateResponse>("/translate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
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
    });
  },
  grammarAnalyze: (payload: { text: string; target_lang: string }) =>
    request<GrammarAnalyzeResponse>("/grammar/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
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
  homeworkSubmit: (payload: { homework_id: number; answers: Record<string, string> }) =>
    request<HomeworkSubmitResponse>("/homework/submit", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  progressSkillMap: (userId: number) =>
    request<ProgressSkillMap>(`/progress/skill-map?user_id=${encodeURIComponent(userId)}`),
  progressStreak: (userId: number) =>
    request<ProgressStreak>(`/progress/streak?user_id=${encodeURIComponent(userId)}`),
  progressJournal: (userId: number) =>
    request<ProgressJournal>(`/progress/journal?user_id=${encodeURIComponent(userId)}`),
  progressWeeklyGoal: (userId: number) =>
    request<WeeklyGoal>(`/progress/weekly-goal?user_id=${encodeURIComponent(userId)}`),
  progressWeeklyGoalSet: (payload: { user_id: number; target_minutes: number }) =>
    request<WeeklyGoal>("/progress/weekly-goal", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
