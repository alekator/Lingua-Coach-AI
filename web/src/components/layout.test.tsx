import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layout";

const mocks = vi.hoisted(() => ({
  openaiKeyStatus: vi.fn(),
  debugOpenai: vi.fn(),
  setTheme: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    openaiKeyStatus: mocks.openaiKeyStatus,
    debugOpenai: mocks.debugOpenai,
  },
}));

vi.mock("./workspace-switcher", () => ({
  WorkspaceSwitcher: () => <div>WorkspaceSwitcher</div>,
}));

vi.mock("../lib/i18n", () => ({
  t: (_locale: string, key: string) => key,
  uiLocaleFromNativeLang: () => "en",
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (
    selector: (state: {
      activeWorkspaceNativeLang: string;
      theme: "light" | "dark-elegant";
      setTheme: typeof mocks.setTheme;
    }) => unknown,
  ) =>
    selector({
      activeWorkspaceNativeLang: "ru",
      theme: "light",
      setTheme: mocks.setTheme,
    }),
}));

function renderLayout() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Routes>
          <Route path="*" element={<AppLayout />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AppLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.openaiKeyStatus.mockResolvedValue({ configured: false });
    mocks.debugOpenai.mockResolvedValue({ status: "ok" });
  });

  it("renders grouped sidebar navigation", async () => {
    renderLayout();
    expect(await screen.findByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Practice")).toBeInTheDocument();
    expect(screen.getByText("Manage")).toBeInTheDocument();
    expect(screen.getByText("nav_dashboard")).toBeInTheDocument();
    expect(screen.getByText("nav_chat")).toBeInTheDocument();
    expect(screen.getByText("nav_profile")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Open profile settings" })).toHaveAttribute(
      "href",
      "/app/profile#openai-key-input",
    );
  });

  it("opens and closes mobile sidebar", async () => {
    const { container } = renderLayout();
    const toggle = screen.getByRole("button", { name: /open menu/i });
    expect(container.querySelector(".app-sidebar")?.classList.contains("open")).toBe(false);

    fireEvent.click(toggle);
    expect(container.querySelector(".app-sidebar")?.classList.contains("open")).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /close menu/i }));
    expect(container.querySelector(".app-sidebar")?.classList.contains("open")).toBe(false);
  });

  it("toggles theme from header icon", async () => {
    renderLayout();
    fireEvent.click(screen.getByRole("button", { name: "Switch to dark elegant theme" }));
    expect(mocks.setTheme).toHaveBeenCalledWith("dark-elegant");
  });

  it("shows quota/billing specific banner when key is saved but unavailable", async () => {
    mocks.openaiKeyStatus.mockResolvedValue({ configured: true });
    mocks.debugOpenai.mockRejectedValue({ status: 429, message: "insufficient_quota" });

    renderLayout();

    expect(await screen.findByText("OpenAI key saved, but quota/billing is unavailable.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review API key settings" })).toHaveAttribute(
      "href",
      "/app/profile#openai-key-input",
    );
  });
});
