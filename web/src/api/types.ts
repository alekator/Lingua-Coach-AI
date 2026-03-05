export type AppBootstrapResponse = {
  user_id: number;
  has_profile: boolean;
  needs_onboarding: boolean;
  next_step: "onboarding" | "dashboard";
  owner_user_id: number;
  active_workspace_id?: number | null;
  active_workspace_native_lang?: string | null;
  active_workspace_target_lang?: string | null;
  active_workspace_goal?: string | null;
};

export type LearningWorkspace = {
  id: number;
  native_lang: string;
  target_lang: string;
  goal?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkspaceListResponse = {
  owner_user_id: number;
  active_workspace_id?: number | null;
  items: LearningWorkspace[];
};

export type WorkspaceSwitchResponse = {
  active_workspace_id: number;
  active_user_id: number;
};

export type WorkspaceOverviewResponse = {
  owner_user_id: number;
  items: Array<{
    workspace_id: number;
    native_lang: string;
    target_lang: string;
    goal?: string | null;
    is_active: boolean;
    has_profile: boolean;
    streak_days: number;
    minutes_practiced: number;
    words_learned: number;
    last_activity_at?: string | null;
  }>;
};

export type WorkspaceDeleteResponse = {
  deleted_workspace_id: number;
  active_workspace_id?: number | null;
};

export type PlacementStartResponse = {
  session_id: number;
  question_index: number;
  question: string;
  total_questions: number;
};

export type PlacementAnswerResponse = {
  session_id: number;
  accepted_question_index: number;
  done: boolean;
  next_question_index?: number | null;
  next_question?: string | null;
};

export type PlacementFinishResponse = {
  session_id: number;
  level: string;
  avg_score: number;
  skill_map: Record<string, number>;
};

export type ProfileResponse = {
  user_id: number;
  native_lang: string;
  target_lang: string;
  level: string;
  goal?: string | null;
  preferences: Record<string, unknown>;
};

export type OpenAIKeyStatus = {
  configured: boolean;
  source: string;
  masked?: string | null;
};

export type OpenAIDebugResponse = {
  status: string;
  detail: string;
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
  adaptation_notes: string[];
};

export type CoachSessionTodayResponse = {
  user_id: number;
  time_budget_minutes: number;
  focus: string[];
  steps: Array<{
    id: string;
    title: string;
    description: string;
    route: string;
    duration_minutes: number;
  }>;
};

export type CoachNextActionsResponse = {
  user_id: number;
  items: Array<{
    id: string;
    title: string;
    reason: string;
    route: string;
    priority: number;
  }>;
};

export type CoachReactivationResponse = {
  user_id: number;
  eligible: boolean;
  gap_days: number;
  weak_topic?: string | null;
  title: string;
  tasks: string[];
  cta_route: string;
  note: string;
};

export type CoachDailyChallengeResponse = {
  user_id: number;
  title: string;
  reason: string;
  task: string;
  route: string;
  estimated_minutes: number;
};

export type CoachTrajectoryResponse = {
  user_id: number;
  horizon_days: number;
  current_phase: string;
  retake_recommended: boolean;
  milestones: Array<{
    day: number;
    title: string;
    target: string;
  }>;
};

export type CoachRoadmapResponse = {
  user_id: number;
  goal: string;
  items: Array<{
    id: string;
    title: string;
    reason: string;
    route: string;
    priority: number;
  }>;
};

export type OutcomePacksResponse = {
  user_id: number;
  items: Array<{
    id: string;
    title: string;
    target_level: string;
    readiness: "ready" | "almost_ready" | "not_ready";
    missing_signals: string[];
    recommended_route: string;
  }>;
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

export type ScenarioScriptResponse = {
  scenario_id: string;
  title: string;
  description: string;
  steps: Array<{
    id: string;
    coach_prompt: string;
    expected_keywords: string[];
    tip: string;
  }>;
};

export type ScenarioTurnResponse = {
  scenario_id: string;
  step_id: string;
  score: number;
  max_score: number;
  feedback: string;
  next_step_id?: string | null;
  next_prompt?: string | null;
  done: boolean;
  suggested_reply?: string | null;
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
  rubric?: Record<
    string,
    {
      is_correct: boolean;
      completeness: number;
      grammar_quality: number;
      lexical_quality: number;
      item_score: number;
      feedback: string;
    }
  >;
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
  rubric?: {
    overall_score: number;
    level_band: string;
    grammar_accuracy: { score: number; feedback: string };
    lexical_range: { score: number; feedback: string };
    fluency_coherence: { score: number; feedback: string };
    task_completion: { score: number; feedback: string };
    strengths: string[];
    priority_fixes: string[];
    next_drill?: string | null;
  } | null;
};

export type VoiceMessageResponse = {
  transcript: string;
  teacher_text: string;
  audio_url: string;
  pronunciation_feedback: string;
  pronunciation_rubric?: {
    fluency: number;
    clarity: number;
    grammar_accuracy: number;
    vocabulary_range: number;
    confidence: number;
    overall_score: number;
    level_band: string;
    actionable_tips: string[];
  };
};

export type VoiceProgressResponse = {
  user_id: number;
  trend: string;
  points: Array<{
    date: string;
    speaking_score: number;
  }>;
  pronunciation_mistakes_7d: number;
  recommendation: string;
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

export type ProgressJournal = {
  weekly_minutes: number;
  weekly_sessions: number;
  weak_areas: string[];
  next_actions: string[];
  entries: Array<{
    session_id: number;
    started_at: string;
    mode: string;
    messages_count: number;
    completed: boolean;
  }>;
};

export type WeeklyGoal = {
  user_id: number;
  target_minutes: number;
  completed_minutes: number;
  remaining_minutes: number;
  completion_percent: number;
  is_completed: boolean;
};

export type ProgressRewards = {
  user_id: number;
  total_xp: number;
  claimed_count: number;
  items: Array<{
    id: string;
    title: string;
    description: string;
    requirement: string;
    xp_points: number;
    status: "locked" | "available" | "claimed";
  }>;
};

export type ProgressWeeklyReview = {
  user_id: number;
  weekly_minutes: number;
  weekly_sessions: number;
  weekly_goal_target_minutes: number;
  weekly_goal_completed: boolean;
  streak_days: number;
  strongest_skill: string;
  weakest_skill: string;
  top_weak_area?: string | null;
  wins: string[];
  next_focus: string;
};

export type ProgressAchievements = {
  user_id: number;
  items: Array<{
    id: string;
    title: string;
    status: "unlocked" | "in_progress";
    progress: string;
  }>;
};

export type ProgressReport = {
  user_id: number;
  period_days: number;
  generated_at: string;
  summary: Record<string, string | number>;
  highlights: string[];
  export_markdown: string;
};
