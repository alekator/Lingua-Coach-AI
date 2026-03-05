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

export type ChatStartResponse = {
  session_id: number;
  mode: string;
  status: string;
};

export type ChatMessageResponse = {
  assistant_text: string;
  corrections: Array<{ type: string; bad: string; good: string; explanation?: string | null }>;
  new_words: Array<{ word: string; translation: string; example?: string | null; phonetics?: string | null }>;
  homework_suggestions: string[];
};

export type VoiceMessageResponse = {
  transcript: string;
  teacher_text: string;
  audio_url: string;
  pronunciation_feedback: string;
};

export type VocabItem = {
  id: number;
  user_id: number;
  word: string;
  translation: string;
  example?: string | null;
  phonetics?: string | null;
  due_at?: string | null;
  interval_days?: number | null;
  ease?: number | null;
};

export type VocabListResponse = {
  items: VocabItem[];
};

export type VocabReviewNextResponse = {
  has_item: boolean;
  item?: VocabItem | null;
};

export type VocabReviewSubmitResponse = {
  vocab_item_id: number;
  rating: string;
  next_due_at: string;
  interval_days: number;
  ease: number;
};

export type HomeworkItem = {
  id: number;
  user_id: number;
  title: string;
  tasks: Array<Record<string, unknown>>;
  status: string;
  created_at: string;
  due_at?: string | null;
};

export type HomeworkListResponse = {
  items: HomeworkItem[];
};

export type HomeworkSubmitResponse = {
  homework_id: number;
  status: string;
  grade: {
    score: number;
    max_score: number;
    feedback: string;
  };
};

export type ProgressSkillMap = {
  speaking: number;
  listening: number;
  grammar: number;
  vocab: number;
  reading: number;
  writing: number;
};

export type ProgressStreak = {
  streak_days: number;
  active_dates: string[];
};
