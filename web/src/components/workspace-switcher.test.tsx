import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { WorkspaceSwitcher } from "./workspace-switcher";

const mocks = vi.hoisted(() => ({
  workspacesList: vi.fn(),
  workspaceSwitch: vi.fn(),
  bootstrap: vi.fn(),
  pushToast: vi.fn(),
  setBootstrapState: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    workspacesList: mocks.workspacesList,
    workspaceSwitch: mocks.workspaceSwitch,
    bootstrap: mocks.bootstrap,
  },
}));

vi.mock("../store/app-store", () => ({
  useAppStore: (
    selector: (state: {
      activeWorkspaceId: number;
      setBootstrapState: typeof mocks.setBootstrapState;
    }) => unknown,
  ) =>
    selector({
      activeWorkspaceId: 1,
      setBootstrapState: mocks.setBootstrapState,
    }),
}));

vi.mock("../store/toast-store", () => ({
  useToastStore: (selector: (state: { push: typeof mocks.pushToast }) => unknown) =>
    selector({ push: mocks.pushToast }),
}));

function renderSwitcher() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <WorkspaceSwitcher />
    </QueryClientProvider>,
  );
}

describe("WorkspaceSwitcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.workspacesList.mockResolvedValue({
      owner_user_id: 1,
      active_workspace_id: 1,
      items: [
        { id: 1, native_lang: "ru", target_lang: "en", is_active: true },
        { id: 2, native_lang: "de", target_lang: "en", is_active: false },
      ],
    });
    mocks.workspaceSwitch.mockResolvedValue({ active_workspace_id: 2, active_user_id: 22 });
    mocks.bootstrap.mockResolvedValue({
      user_id: 22,
      has_profile: true,
      needs_onboarding: false,
      next_step: "dashboard",
      owner_user_id: 1,
      active_workspace_id: 2,
    });
  });

  it("switches workspace and syncs bootstrap context", async () => {
    renderSwitcher();

    await waitFor(() => {
      expect(screen.getByLabelText("Space")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Space"), { target: { value: "2" } });

    await waitFor(() => {
      expect(mocks.workspaceSwitch).toHaveBeenCalledWith({ workspace_id: 2 });
      expect(mocks.setBootstrapState).toHaveBeenCalledWith(
        expect.objectContaining({
          userId: 22,
          hasProfile: true,
          ownerUserId: 1,
          activeWorkspaceId: 2,
        }),
      );
    });
  });
});

