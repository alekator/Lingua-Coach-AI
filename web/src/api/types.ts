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

export type AppResetResponse = {
  status: string;
  deleted_users: number;
  deleted_workspaces: number;
  deleted_profiles: number;
  deleted_vocab_items: number;
  deleted_chat_sessions: number;
  openai_key_cleared: boolean;
};

export type AppBackupExportResponse = {
  version: number;
  exported_at: string;
  snapshot: Record<string, unknown>;
};

export type AppBackupRestoreResponse = {
  status: string;
  restored_tables: Record<string, number>;
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
  persistent?: boolean;
  secure_storage?: boolean;
};

export type UsageBudgetStatus = {
  user_id: number;
  daily_token_cap: number;
  weekly_token_cap: number;
  warning_threshold: number;
  daily_used_tokens: number;
  weekly_used_tokens: number;
  daily_remaining_tokens: number;
  weekly_remaining_tokens: number;
  daily_warning: boolean;
  weekly_warning: boolean;
  blocked: boolean;
};

export type LanguageCapabilities = {
  native_lang: string;
  target_lang: string;
  text_supported: boolean;
  asr_supported: boolean;
  tts_supported: boolean;
  voice_supported: boolean;
  recommendation: string;
};

export type OpenAIDebugResponse = {
  status: string;
  detail: string;
};

export type AIModuleDiagnostics = {
  provider: "openai" | "local";
  status: string;
  message: string;
  model_path?: string | null;
  model_exists: boolean;
  dependency_available: boolean;
  device?: string | null;
  load_ms?: number | null;
  probe_ms?: number | null;
};

export type AIRuntimeStatus = {
  llm_provider: "openai" | "local";
  asr_provider: "openai" | "local";
  tts_provider: "openai" | "local";
  llm: AIModuleDiagnostics;
  asr: AIModuleDiagnostics;
  tts: AIModuleDiagnostics;
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

export type CoachSessionProgressResponse = {
  user_id: number;
  session_date: string;
  total_steps: number;
  completed_steps: number;
  completion_percent: number;
  items: Array<{
    step_id: string;
    title: string;
    status: "pending" | "in_progress" | "completed";
    started_at?: string | null;
    completed_at?: string | null;
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
    quick_mode_minutes?: number | null;
  }>;
};

export type CoachReviewQueueResponse = {
  user_id: number;
  items: Array<{
    id: string;
    type: string;
    title: string;
    reason: string;
    route: string;
    estimated_minutes: number;
    priority: number;
    due_now: boolean;
  }>;
};

export type CoachErrorBankResponse = {
  user_id: number;
  items: Array<{
    category: string;
    occurrences: number;
    latest_bad: string;
    latest_good: string;
    latest_explanation?: string | null;
    last_seen_at: string;
    drill_prompt: string;
    suggested_route: string;
  }>;
};

export type CoachReactivationResponse = {
  user_id: number;
  eligible: boolean;
  gap_days: number;
  available_minutes: number;
  recommended_minutes: number;
  plan_mode: string;
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
  required_level: string;
  unlocked: boolean;
  gate_reason?: string | null;
};

export type ScenariosResponse = {
  items: ScenarioItem[];
};

export type CoachScenarioTracksResponse = {
  user_id: number;
  items: Array<{
    track_id: string;
    goal: string;
    title: string;
    total_steps: number;
    completed_steps: number;
    completion_percent: number;
    next_scenario_id?: string | null;
    steps: Array<{
      order: number;
      scenario_id: string;
      title: string;
      status: "completed" | "available" | "locked";
    }>;
    milestones: Array<{
      id: string;
      title: string;
      required_completed: number;
      is_reached: boolean;
    }>;
  }>;
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

export type GrammarHistoryItem = {
  id: number;
  target_lang: string;
  input_text: string;
  corrected_text: string;
  errors: Array<{
    category: string;
    bad: string;
    good: string;
    explanation: string;
  }>;
  exercises: string[];
  created_at: string;
};

export type GrammarHistoryResponse = {
  items: GrammarHistoryItem[];
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
  engine_used?: "openai" | "local" | "fallback" | string;
};

export type TranslateVoiceResponse = {
  transcript: string;
  translated_text: string;
  audio_url: string;
  engine_used?: "openai" | "local" | "fallback" | string;
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
  engine_used?: "openai" | "local" | "fallback" | string;
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
  enrichment_source?: "openai" | "local" | "fallback" | "manual" | string | null;
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
  submission_count: number;
  latest_score?: number | null;
  latest_feedback?: string | null;
  latest_answer_text?: string | null;
};

export type HomeworkListResponse = {
  items: HomeworkItem[];
};

export type HomeworkDeleteResponse = {
  deleted_homework_id: number;
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

export type ProgressSkillTree = {
  user_id: number;
  current_level: string;
  estimated_level_from_skills: string;
  avg_skill_score: number;
  next_target_level?: string | null;
  items: Array<{
    level: string;
    status: "completed" | "in_progress" | "locked";
    progress_percent: number;
    closed_criteria: string[];
    remaining_criteria: string[];
  }>;
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

export type ProgressTimeline = {
  user_id: number;
  workspace_id?: number | null;
  skill_filter?: string | null;
  activity_type_filter?: string | null;
  items: Array<{
    id: string;
    workspace_id?: number | null;
    workspace_label?: string | null;
    activity_type: string;
    skill_tags: string[];
    title: string;
    detail: string;
    happened_at: string;
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

export type ProgressWeeklyCheckpoint = {
  user_id: number;
  window_days: number;
  baseline_at?: string | null;
  current_at?: string | null;
  baseline_avg_skill: number;
  current_avg_skill: number;
  delta_points: number;
  delta_percent: number;
  measurable_growth: boolean;
  top_gain_skill: string;
  top_gain_points: number;
  skills: Array<{
    skill: string;
    before: number;
    after: number;
    delta: number;
  }>;
  summary: string;
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
