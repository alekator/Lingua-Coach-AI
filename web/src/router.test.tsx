import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AppRouter } from "./router";

function renderRouter(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AppRouter />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AppRouter bootstrap gate", () => {
  it("redirects to onboarding on first run", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          user_id: 1,
          has_profile: false,
          needs_onboarding: true,
          next_step: "onboarding",
        }),
      }),
    );

    renderRouter("/app");

    await waitFor(() => {
      expect(screen.getByText("First Launch Setup")).toBeInTheDocument();
    });
  });

  it("redirects to dashboard when profile exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/app/bootstrap")) {
          return {
            ok: true,
            json: async () => ({
              user_id: 1,
              has_profile: true,
              needs_onboarding: false,
              next_step: "dashboard",
            }),
          };
        }
        if (url.includes("/progress/summary")) {
          return {
            ok: true,
            json: async () => ({
              streak_days: 2,
              minutes_practiced: 16,
              words_learned: 10,
              speaking: 50,
              listening: 52,
              grammar: 48,
              vocab: 55,
              reading: 53,
              writing: 47,
            }),
          };
        }
        return {
          ok: true,
          json: async () => ({
            user_id: 1,
            time_budget_minutes: 15,
            focus: ["grammar", "speaking", "vocab"],
            tasks: ["A", "B", "C"],
          }),
        };
      }),
    );

    renderRouter("/");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    });
  });
});
