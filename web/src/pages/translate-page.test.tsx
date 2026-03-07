import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { TranslatePage } from "./translate-page";

const mocks = vi.hoisted(() => ({
  translate: vi.fn(),
  translateVoice: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    translate: mocks.translate,
    translateVoice: mocks.translateVoice,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (
    selector: (state: { userId: number; activeWorkspaceNativeLang: string | null; activeWorkspaceTargetLang: string | null }) => unknown,
  ) =>
    selector({
      userId: 1,
      activeWorkspaceNativeLang: "de",
      activeWorkspaceTargetLang: "en",
    }),
}));

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) =>
    selector({ push: mocks.pushToast }),
}));

describe("TranslatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    mocks.translate.mockResolvedValue({
      translated_text: "hello world",
      audio_url: null,
      engine_used: "openai",
    });
    mocks.translateVoice.mockResolvedValue({
      transcript: "hallo welt",
      translated_text: "hello world",
      audio_url: "http://tts.local/audio/1.mp3",
    });
  });

  it("uses active workspace language pair as defaults", async () => {
    render(<TranslatePage />);

    expect(screen.getByDisplayValue("de")).toBeInTheDocument();
    expect(screen.getByDisplayValue("en")).toBeInTheDocument();
    expect(screen.getByText("Smart pair from active space: DE -> EN")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Translate text" }));

    await waitFor(() => {
      expect(mocks.translate).toHaveBeenCalledWith({
        user_id: 1,
        text: "Hello world",
        source_lang: "de",
        target_lang: "en",
        voice: true,
      });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Text translated");
      expect(screen.getAllByText("OpenAI").length).toBeGreaterThan(0);
    });
  });

  it("loads memory feed from localStorage on page reload", async () => {
    window.localStorage.setItem(
      "translate-memory:v2:user:1",
      JSON.stringify([
        {
          id: "txt-1",
          kind: "text",
          sourceLang: "de",
          targetLang: "en",
          inputText: "Guten Morgen",
          outputText: "Good morning",
          engine: "local",
          createdAt: "2026-03-07T10:00:00.000Z",
        },
      ]),
    );

    render(<TranslatePage />);

    await waitFor(() => {
      expect(screen.getByText("Guten Morgen")).toBeInTheDocument();
      expect(screen.getByText("Good morning")).toBeInTheDocument();
      expect(screen.getAllByText("Local").length).toBeGreaterThan(0);
    });
  });
});
