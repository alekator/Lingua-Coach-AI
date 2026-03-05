import { create } from "zustand";

type AppState = {
  userId: number | null;
  ownerUserId: number | null;
  activeWorkspaceId: number | null;
  hasProfile: boolean;
  dailyMinutes: number;
  strictness: "low" | "medium" | "high";
  setBootstrapState: (payload: {
    userId: number;
    hasProfile: boolean;
    ownerUserId?: number | null;
    activeWorkspaceId?: number | null;
  }) => void;
  setCoachPrefs: (payload: { dailyMinutes: number; strictness: "low" | "medium" | "high" }) => void;
  setDailyMinutes: (minutes: number) => void;
};

export const useAppStore = create<AppState>((set) => ({
  userId: null,
  ownerUserId: null,
  activeWorkspaceId: null,
  hasProfile: false,
  dailyMinutes: 15,
  strictness: "medium",
  setBootstrapState: (payload) =>
    set({
      userId: payload.userId,
      hasProfile: payload.hasProfile,
      ownerUserId: payload.ownerUserId ?? null,
      activeWorkspaceId: payload.activeWorkspaceId ?? null,
    }),
  setCoachPrefs: (payload) =>
    set({
      dailyMinutes: payload.dailyMinutes,
      strictness: payload.strictness,
    }),
  setDailyMinutes: (minutes) => set({ dailyMinutes: Math.max(5, Math.min(120, minutes)) }),
}));
