import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ProfilePage } from "./profile-page";

const mocks = vi.hoisted(() => ({
  profileGet: vi.fn(),
  profileSetup: vi.fn(),
  progressSkillMap: vi.fn(),
  progressStreak: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    profileGet: mocks.profileGet,
    profileSetup: mocks.profileSetup,
    progressSkillMap: mocks.progressSkillMap,
    progressStreak: mocks.progressStreak,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (selector: (state: { userId: number }) => unknown) => selector({ userId: 1 }),
}));

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) =>
    selector({ push: mocks.pushToast }),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProfilePage />
    </QueryClientProvider>,
  );
}

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.profileGet.mockResolvedValue({
      user_id: 1,
      native_lang: "ru",
      target_lang: "en",
      level: "B1",
      goal: "work",
      preferences: { strictness: "medium" },
    });
    mocks.progressSkillMap.mockResolvedValue({
      speaking: 50,
      listening: 52,
      grammar: 48,
      vocab: 55,
      reading: 53,
      writing: 47,
    });
    mocks.progressStreak.mockResolvedValue({
      streak_days: 2,
      active_dates: ["2026-03-05", "2026-03-06"],
    });
    mocks.profileSetup.mockResolvedValue({});
  });

  it("loads profile settings and saves edits", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByDisplayValue("ru")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Goal"), { target: { value: "travel" } });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => {
      expect(mocks.profileSetup).toHaveBeenCalledWith(
        expect.objectContaining({
          user_id: 1,
          native_lang: "ru",
          target_lang: "en",
          level: "B1",
          goal: "travel",
        }),
      );
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Profile updated");
    });
  });
});
