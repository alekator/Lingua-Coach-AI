import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VoicePage } from "./voice-page";

const mocks = vi.hoisted(() => ({
  voiceMessage: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    voiceMessage: mocks.voiceMessage,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (selector: (state: { userId: number }) => unknown) => selector({ userId: 1 }),
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
  });

  it("renders structured feedback and supports coach-target retry", async () => {
    render(<VoicePage />);

    const fileInput = screen.getByLabelText("Upload voice sample (10-45 sec)") as HTMLInputElement;
    const file = new File(["voice-bytes"], "voice.webm", { type: "audio/webm" });
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Process voice" }));

    await waitFor(() => {
      expect(screen.getByText("Coach Voice Feedback")).toBeInTheDocument();
      expect(screen.getByText("Transcript: I goed to school")).toBeInTheDocument();
      expect(screen.getByText(/Rubric: 56 \(developing\)/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Use coach target for next try" }));

    await waitFor(() => {
      const phraseInput = screen.getByPlaceholderText("Example: I went to school yesterday.") as HTMLInputElement;
      expect(phraseInput.value).toBe("I went to school");
      expect(mocks.pushToast).toHaveBeenCalledWith("info", "Coach target applied for retry");
    });
  });
});
