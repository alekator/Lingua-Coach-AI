import { create } from "zustand";

type AppState = {
  theme: "light" | "dark-elegant";
  userId: number | null;
  ownerUserId: number | null;
  activeWorkspaceId: number | null;
  activeWorkspaceNativeLang: string | null;
  activeWorkspaceTargetLang: string | null;
  activeWorkspaceGoal: string | null;
  hasProfile: boolean;
  dailyMinutes: number;
  strictness: "low" | "medium" | "high";
  setBootstrapState: (payload: {
    userId: number;
    hasProfile: boolean;
    ownerUserId?: number | null;
    activeWorkspaceId?: number | null;
    activeWorkspaceNativeLang?: string | null;
    activeWorkspaceTargetLang?: string | null;
    activeWorkspaceGoal?: string | null;
  }) => void;
  setCoachPrefs: (payload: { dailyMinutes: number; strictness: "low" | "medium" | "high" }) => void;
  setDailyMinutes: (minutes: number) => void;
  setTheme: (theme: "light" | "dark-elegant") => void;
};

function initialTheme(): "light" | "dark-elegant" {
  if (typeof window === "undefined") return "light";
  const saved = window.localStorage.getItem("linguacoach_theme");
  if (saved === "dark-elegant") return "dark-elegant";
  return "light";
}

export const useAppStore = create<AppState>((set) => ({
  theme: initialTheme(),
  userId: null,
  ownerUserId: null,
  activeWorkspaceId: null,
  activeWorkspaceNativeLang: null,
  activeWorkspaceTargetLang: null,
  activeWorkspaceGoal: null,
  hasProfile: false,
  dailyMinutes: 15,
  strictness: "medium",
  setBootstrapState: (payload) =>
    set({
      userId: payload.userId,
      hasProfile: payload.hasProfile,
      ownerUserId: payload.ownerUserId ?? null,
      activeWorkspaceId: payload.activeWorkspaceId ?? null,
      activeWorkspaceNativeLang: payload.activeWorkspaceNativeLang ?? null,
      activeWorkspaceTargetLang: payload.activeWorkspaceTargetLang ?? null,
      activeWorkspaceGoal: payload.activeWorkspaceGoal ?? null,
    }),
  setCoachPrefs: (payload) =>
    set({
      dailyMinutes: payload.dailyMinutes,
      strictness: payload.strictness,
    }),
  setDailyMinutes: (minutes) => set({ dailyMinutes: Math.max(5, Math.min(120, minutes)) }),
  setTheme: (theme) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("linguacoach_theme", theme);
    }
    set({ theme });
  },
}));
