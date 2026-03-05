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
