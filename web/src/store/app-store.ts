import { create } from "zustand";

type AppState = {
  userId: number | null;
  hasProfile: boolean;
  setBootstrapState: (payload: { userId: number; hasProfile: boolean }) => void;
};

export const useAppStore = create<AppState>((set) => ({
  userId: null,
  hasProfile: false,
  setBootstrapState: (payload) => set({ userId: payload.userId, hasProfile: payload.hasProfile }),
}));
