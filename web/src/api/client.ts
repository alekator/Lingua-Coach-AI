import type { AppBootstrapResponse, ProgressSummary } from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${response.status}: ${text}`);
  }
  return (await response.json()) as T;
}

export const api = {
  bootstrap: () => request<AppBootstrapResponse>("/app/bootstrap"),
  profileSetup: (payload: {
    user_id: number;
    native_lang: string;
    target_lang: string;
    level: string;
    goal?: string;
    preferences?: Record<string, unknown>;
  }) =>
    request("/profile/setup", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  progressSummary: (userId: number) =>
    request<ProgressSummary>(`/progress/summary?user_id=${encodeURIComponent(userId)}`),
};
