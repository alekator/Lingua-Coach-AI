import { create } from "zustand";

export type ToastKind = "success" | "error" | "info";

export type Toast = {
  id: string;
  kind: ToastKind;
  message: string;
};

type ToastState = {
  toasts: Toast[];
  push: (kind: ToastKind, message: string) => void;
  remove: (id: string) => void;
};

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (kind, message) =>
    set((state) => {
      const id = crypto.randomUUID();
      const next = [...state.toasts, { id, kind, message }];
      setTimeout(() => {
        set((inner) => ({ toasts: inner.toasts.filter((t) => t.id !== id) }));
      }, 3500);
      return { toasts: next };
    }),
  remove: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
