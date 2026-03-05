import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiError } from "../api/client";
import { GrammarPage } from "./grammar-page";

const mocks = vi.hoisted(() => ({
  grammarAnalyze: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return {
    ...actual,
    api: {
      grammarAnalyze: mocks.grammarAnalyze,
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
  beforeEach(() => {
    vi.clearAllMocks();
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

    render(<GrammarPage />);

    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));

    await waitFor(() => {
      expect(screen.getByText("Corrected: I went to school")).toBeInTheDocument();
      expect(screen.getByText("Use irregular verb.")).toBeInTheDocument();
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Grammar analysis completed");
      expect(mocks.grammarAnalyze).toHaveBeenCalledWith({ text: "I goed to school", target_lang: "fr" });
    });
  });

  it("shows error state when analysis fails", async () => {
    mocks.grammarAnalyze.mockRejectedValue(new ApiError("bad input", 400, "req-grammar"));

    render(<GrammarPage />);
    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));

    await waitFor(() => {
      expect(screen.getByText("HTTP 400: bad input (request req-grammar)")).toBeInTheDocument();
      expect(mocks.pushToast).toHaveBeenCalledWith("error", "HTTP 400: bad input (request req-grammar)");
    });
  });
});
