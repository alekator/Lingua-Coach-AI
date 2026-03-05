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
    selector: (state: { activeWorkspaceNativeLang: string | null; activeWorkspaceTargetLang: string | null }) => unknown,
  ) =>
    selector({
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
    mocks.translate.mockResolvedValue({
      translated_text: "hello world",
      audio_url: null,
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
    expect(screen.getByText("Default pair from active space: DE -> EN")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Translate text" }));

    await waitFor(() => {
      expect(mocks.translate).toHaveBeenCalledWith({
        text: "Hello world",
        source_lang: "de",
        target_lang: "en",
        voice: true,
      });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Text translated");
    });
  });
});
