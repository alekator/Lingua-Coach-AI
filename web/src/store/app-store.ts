import { create } from "zustand";

type AppState = {
  userId: number | null;
  hasProfile: boolean;
  dailyMinutes: number;
  strictness: "low" | "medium" | "high";
  setBootstrapState: (payload: { userId: number; hasProfile: boolean }) => void;
  setCoachPrefs: (payload: { dailyMinutes: number; strictness: "low" | "medium" | "high" }) => void;
};

export const useAppStore = create<AppState>((set) => ({
  userId: null,
  hasProfile: false,
  dailyMinutes: 15,
  strictness: "medium",
  setBootstrapState: (payload) => set({ userId: payload.userId, hasProfile: payload.hasProfile }),
  setCoachPrefs: (payload) =>
    set({
      dailyMinutes: payload.dailyMinutes,
      strictness: payload.strictness,
    }),
}));
