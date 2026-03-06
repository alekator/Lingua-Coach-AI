import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "../api/client";
import { GrammarPage } from "./grammar-page";

const mocks = vi.hoisted(() => ({
  grammarAnalyze: vi.fn(),
  grammarHistory: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return {
    ...actual,
    api: {
      grammarAnalyze: mocks.grammarAnalyze,
      grammarHistory: mocks.grammarHistory,
    },
  };
});

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) =>
    selector({ push: mocks.pushToast }),
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (selector: (state: { activeWorkspaceTargetLang: string | null }) => unknown) =>
    selector({ activeWorkspaceTargetLang: "fr" }),
}));

describe("GrammarPage", () => {
  function renderPage() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return render(
      <QueryClientProvider client={queryClient}>
        <GrammarPage />
      </QueryClientProvider>,
    );
  }

  beforeEach(() => {
    vi.clearAllMocks();
    mocks.grammarHistory.mockResolvedValue({ items: [] });
  });

  it("analyzes text and renders corrections", async () => {
    mocks.grammarAnalyze.mockResolvedValue({
      corrected_text: "I went to school",
      errors: [
        {
          category: "grammar",
          bad: "goed",
          good: "went",
          explanation: "Use irregular verb.",
        },
      ],
      exercises: ["Rewrite with 'went'"],
    });

    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Corrected Answer" })).toBeInTheDocument();
      expect(screen.getByText("I went to school")).toBeInTheDocument();
      expect(screen.getByText("Use irregular verb.")).toBeInTheDocument();
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Grammar analysis completed");
      expect(mocks.grammarAnalyze).toHaveBeenCalledWith({ user_id: 1, text: "I goed to school", target_lang: "fr" });
    });
  });

  it("shows error state when analysis fails", async () => {
    mocks.grammarAnalyze.mockRejectedValue(new ApiError("bad input", 400, "req-grammar"));

    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));

    await waitFor(() => {
      expect(screen.getByText("HTTP 400: bad input (request req-grammar)")).toBeInTheDocument();
      expect(mocks.pushToast).toHaveBeenCalledWith("error", "HTTP 400: bad input (request req-grammar)");
    });
  });

  it("renders history list from backend", async () => {
    mocks.grammarHistory.mockResolvedValue({
      items: [
        {
          id: 77,
          target_lang: "fr",
          input_text: "I has a book",
          corrected_text: "I have a book",
          errors: [],
          exercises: [],
          created_at: "2026-03-07T00:00:00Z",
        },
      ],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Answer Memory" })).toBeInTheDocument();
      expect(screen.getByText("I has a book")).toBeInTheDocument();
      expect(screen.getByText("I have a book")).toBeInTheDocument();
      expect(mocks.grammarHistory).toHaveBeenCalledWith(1, 40);
    });
  });
});
