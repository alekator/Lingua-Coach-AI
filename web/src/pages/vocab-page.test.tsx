import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VocabPage } from "./vocab-page";

const mocks = vi.hoisted(() => ({
  vocabList: vi.fn(),
  vocabAdd: vi.fn(),
  vocabReviewNext: vi.fn(),
  vocabReviewSubmit: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    vocabList: mocks.vocabList,
    vocabAdd: mocks.vocabAdd,
    vocabReviewNext: mocks.vocabReviewNext,
    vocabReviewSubmit: mocks.vocabReviewSubmit,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (selector: (state: { userId: number }) => unknown) => selector({ userId: 1 }),
}));

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) => selector({ push: mocks.pushToast }),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <VocabPage />
    </QueryClientProvider>,
  );
}

describe("VocabPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.vocabList.mockResolvedValue({
      items: [
        {
          id: 9,
          user_id: 1,
          word: "achieve",
          translation: "добиваться",
          example: "I want to achieve this goal.",
          phonetics: "əˈtʃiːv",
          enrichment_source: "openai",
          due_at: null,
          interval_days: 2,
          ease: 2.5,
        },
      ],
    });
    mocks.vocabAdd.mockResolvedValue({});
    mocks.vocabReviewNext.mockResolvedValue({
      has_item: true,
      item: {
        id: 9,
        user_id: 1,
        word: "achieve",
        translation: "добиваться",
        example: "I want to achieve this goal.",
        phonetics: "əˈtʃiːv",
        enrichment_source: "openai",
        due_at: null,
        interval_days: 2,
        ease: 2.5,
      },
    });
    mocks.vocabReviewSubmit.mockResolvedValue({
      vocab_item_id: 9,
      rating: "good",
      next_due_at: "2026-03-08T00:00:00Z",
      interval_days: 4,
      ease: 2.6,
    });
  });

  it("renders redesigned vocab layout", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Word Bank + SRS" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Review Studio" })).toBeInTheDocument();
      expect(screen.getByText("I want to achieve this goal.")).toBeInTheDocument();
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });
  });

  it("adds word via API", async () => {
    renderPage();

    await screen.findByLabelText("Word");
    fireEvent.change(screen.getByLabelText("Word"), { target: { value: "improve" } });
    fireEvent.change(screen.getByLabelText("Translation"), { target: { value: "улучшать" } });
    fireEvent.click(screen.getByRole("button", { name: "Save to bank" }));

    await waitFor(() => {
      expect(mocks.vocabAdd).toHaveBeenCalledWith({
        user_id: 1,
        word: "improve",
        translation: "улучшать",
      });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Word added with AI enrichment");
    });
  });

  it("loads due card and submits review rating", async () => {
    renderPage();

    await screen.findByRole("button", { name: "Load next review card" });
    fireEvent.click(screen.getByRole("button", { name: "Load next review card" }));

    await screen.findByRole("button", { name: "Good" });
    fireEvent.click(screen.getByRole("button", { name: "Good" }));

    await waitFor(() => {
      expect(mocks.vocabReviewNext).toHaveBeenCalledWith({ user_id: 1 });
      expect(mocks.vocabReviewSubmit).toHaveBeenCalledWith({
        user_id: 1,
        vocab_item_id: 9,
        rating: "good",
      });
    });
  });
});
