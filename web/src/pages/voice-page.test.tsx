import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VoicePage } from "./voice-page";

const mocks = vi.hoisted(() => ({
  voiceMessage: vi.fn(),
  voiceProgress: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    voiceMessage: mocks.voiceMessage,
    voiceProgress: mocks.voiceProgress,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (selector: (state: { userId: number; activeWorkspaceTargetLang: string | null }) => unknown) =>
    selector({ userId: 1, activeWorkspaceTargetLang: "de" }),
}));

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) =>
    selector({ push: mocks.pushToast }),
}));

describe("VoicePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.voiceMessage.mockResolvedValue({
      transcript: "I goed to school",
      teacher_text: "You should say: I went to school.",
      audio_url: "http://tts.local/audio/voice.mp3",
      pronunciation_feedback: "Improve rhythm and stress.",
      pronunciation_rubric: {
        fluency: 58,
        clarity: 62,
        grammar_accuracy: 45,
        vocabulary_range: 61,
        confidence: 57,
        overall_score: 56,
        level_band: "developing",
        actionable_tips: ["Speak slower in short chunks."],
      },
    });
    mocks.voiceProgress.mockResolvedValue({
      user_id: 1,
      trend: "improving",
      points: [
        { date: "2026-03-01", speaking_score: 44 },
        { date: "2026-03-02", speaking_score: 51 },
        { date: "2026-03-03", speaking_score: 58 },
      ],
      pronunciation_mistakes_7d: 2,
      recommendation: "Run 3 short pronunciation retries on the same phrase this week.",
    });
  });

  it("renders structured feedback and supports coach-target retry", async () => {
    render(<VoicePage />);

    expect(screen.getByText("Sentence Challenge")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New sentence" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Use for retry" })).toBeInTheDocument();

    const fileInput = screen.getByLabelText("Upload voice sample (10-45 sec)") as HTMLInputElement;
    const file = new File(["voice-bytes"], "voice.webm", { type: "audio/webm" });
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze voice" }));

    await waitFor(() => {
      expect(screen.getByText("Coach feedback")).toBeInTheDocument();
      expect(screen.getAllByText("I goed to school").length).toBeGreaterThan(0);
      expect(screen.getByText(/56 • developing/)).toBeInTheDocument();
      expect(screen.getByText("Dynamic metrics")).toBeInTheDocument();
      expect(mocks.voiceMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          user_id: 1,
          target_lang: "de",
          language_hint: "de",
        }),
      );
      expect(mocks.voiceProgress).toHaveBeenCalledWith(1);
    });

    fireEvent.click(screen.getByRole("button", { name: "Use coach target for retry" }));

    await waitFor(() => {
      const phraseInput = screen.getByPlaceholderText("Example: I went to school yesterday.") as HTMLInputElement;
      expect(phraseInput.value).toBe("I went to school");
      expect(mocks.pushToast).toHaveBeenCalledWith("info", "Coach target applied for retry");
    });
  });
});
