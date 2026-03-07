import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ChatPage } from "./chat-page";

const mocks = vi.hoisted(() => ({
  chatStart: vi.fn(),
  chatMessage: vi.fn(),
  chatEnd: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    chatStart: mocks.chatStart,
    chatMessage: mocks.chatMessage,
    chatEnd: mocks.chatEnd,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (selector: (state: { userId: number }) => unknown) => selector({ userId: 1 }),
}));

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) =>
    selector({ push: mocks.pushToast }),
}));

describe("ChatPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts session, sends message and renders rubric", async () => {
    mocks.chatStart.mockResolvedValue({
      session_id: 42,
      mode: "chat",
      status: "started",
    });
    mocks.chatMessage.mockResolvedValue({
      assistant_text: "Good try. Let's refine your collocation.",
      engine_used: "openai",
      corrections: [
        {
          type: "grammar",
          bad: "I did a mistake",
          good: "I made a mistake",
          explanation: "Use make + mistake",
        },
      ],
      new_words: [],
      homework_suggestions: ["Write 3 new sentences with 'make a mistake'."],
      rubric: {
        overall_score: 72,
        level_band: "developing",
        grammar_accuracy: { score: 3, feedback: "Fix collocations and tense control." },
        lexical_range: { score: 3, feedback: "Reuse one topic word in each sentence." },
        fluency_coherence: { score: 4, feedback: "Ideas are clear and sequential." },
        task_completion: { score: 4, feedback: "You answered the intent of the prompt." },
        strengths: ["Clear message intent"],
        priority_fixes: ["I did a mistake -> I made a mistake"],
        next_drill: "Write 3 short lines about yesterday plans.",
      },
    });

    render(<ChatPage />);

    fireEvent.click(screen.getByRole("button", { name: "Start session" }));
    await waitFor(() => {
      expect(screen.getByText("Coach session 42 started")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Send to coach" }));
    await waitFor(() => {
      expect(screen.getByText("Live insights")).toBeInTheDocument();
      expect(screen.getByText("Last coach feedback")).toBeInTheDocument();
      expect(screen.getByText("Overall: 72/100 (developing)")).toBeInTheDocument();
      expect(screen.getByText("Grammar: 3/5")).toBeInTheDocument();
      expect(screen.getByText("I did a mistake -> I made a mistake")).toBeInTheDocument();
      expect(screen.getAllByText("OpenAI").length).toBeGreaterThan(0);
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Chat session started");
    });
  });
});
