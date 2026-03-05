export type AppBootstrapResponse = {
  user_id: number;
  has_profile: boolean;
  needs_onboarding: boolean;
  next_step: "onboarding" | "dashboard";
};

export type ProgressSummary = {
  streak_days: number;
  minutes_practiced: number;
  words_learned: number;
  speaking: number;
  listening: number;
  grammar: number;
  vocab: number;
  reading: number;
  writing: number;
};

export type PlanTodayResponse = {
  user_id: number;
  time_budget_minutes: number;
  focus: string[];
  tasks: string[];
};

export type ScenarioItem = {
  id: string;
  title: string;
  description: string;
};

export type ScenariosResponse = {
  items: ScenarioItem[];
};

export type ScenarioSelectResponse = {
  session_id: number;
  mode: string;
};

export type GrammarAnalyzeResponse = {
  corrected_text: string;
  errors: Array<{
    category: string;
    bad: string;
    good: string;
    explanation: string;
  }>;
  exercises: string[];
};

export type ExercisesGenerateResponse = {
  items: Array<{
    id: string;
    type: string;
    prompt: string;
    expected_answer: string;
  }>;
};

export type ExercisesGradeResponse = {
  score: number;
  max_score: number;
  details: Record<string, boolean>;
};

export type TranslateResponse = {
  translated_text: string;
  source_lang: string;
  target_lang: string;
  audio_url?: string | null;
};

export type TranslateVoiceResponse = {
  transcript: string;
  translated_text: string;
  audio_url: string;
};
