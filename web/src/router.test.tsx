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
});
