import type {
  AppBootstrapResponse,
  ExercisesGenerateResponse,
  ExercisesGradeResponse,
  GrammarAnalyzeResponse,
  PlanTodayResponse,
  ProgressSummary,
  ScenarioSelectResponse,
  ScenariosResponse,
  TranslateResponse,
  TranslateVoiceResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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
    throw new Error(`API ${response.status}: ${text}`);
  }
  return (await response.json()) as T;
}

export const api = {
  bootstrap: () => request<AppBootstrapResponse>("/app/bootstrap"),
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
  progressSummary: (userId: number) =>
    request<ProgressSummary>(`/progress/summary?user_id=${encodeURIComponent(userId)}`),
  planToday: (userId: number, timeBudgetMinutes = 15) =>
    request<PlanTodayResponse>(
      `/plan/today?user_id=${encodeURIComponent(userId)}&time_budget_minutes=${encodeURIComponent(timeBudgetMinutes)}`,
    ),
  scenarios: () => request<ScenariosResponse>("/scenarios"),
  selectScenario: (payload: { user_id: number; scenario_id: string }) =>
    request<ScenarioSelectResponse>("/scenarios/select", {
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
};
