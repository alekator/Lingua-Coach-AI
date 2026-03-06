import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { HomeworkPage } from "./homework-page";

const mocks = vi.hoisted(() => ({
  homeworkList: vi.fn(),
  homeworkCreate: vi.fn(),
  homeworkSubmit: vi.fn(),
  homeworkUpdate: vi.fn(),
  homeworkDelete: vi.fn(),
  pushToast: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    homeworkList: mocks.homeworkList,
    homeworkCreate: mocks.homeworkCreate,
    homeworkSubmit: mocks.homeworkSubmit,
    homeworkUpdate: mocks.homeworkUpdate,
    homeworkDelete: mocks.homeworkDelete,
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
      <HomeworkPage />
    </QueryClientProvider>,
  );
}

describe("HomeworkPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.homeworkList.mockResolvedValue({
      items: [
        {
          id: 12,
          user_id: 1,
          title: "Daily grammar drill",
          tasks: [{ id: "response", type: "freeform", prompt: "Fix 5 sentences in past tense." }],
          status: "assigned",
          created_at: "2026-03-07T00:00:00Z",
          due_at: null,
          submission_count: 0,
          latest_score: null,
          latest_feedback: null,
          latest_answer_text: null,
        },
      ],
    });
    mocks.homeworkCreate.mockResolvedValue({});
    mocks.homeworkSubmit.mockResolvedValue({
      homework_id: 12,
      status: "submitted",
      grade: { score: 0.85, max_score: 1, feedback: "Good" },
    });
    mocks.homeworkUpdate.mockResolvedValue({});
    mocks.homeworkDelete.mockResolvedValue({ deleted_homework_id: 12 });
  });

  it("renders redesigned homework layout", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Coach Homework" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Homework Progress" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Daily grammar drill" })).toBeInTheDocument();
    });
  });

  it("creates homework card with title and prompt", async () => {
    renderPage();

    await screen.findByLabelText("Homework title");
    fireEvent.change(screen.getByLabelText("Homework title"), { target: { value: "Writing task" } });
    fireEvent.change(screen.getByLabelText("Assignment prompt"), {
      target: { value: "Write a 120-word story using 5 irregular verbs." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create homework" }));

    await waitFor(() => {
      expect(mocks.homeworkCreate).toHaveBeenCalledWith({
        user_id: 1,
        title: "Writing task",
        tasks: [{ id: "response", type: "freeform", prompt: "Write a 120-word story using 5 irregular verbs." }],
      });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Homework created");
    });
  });

  it("submits homework answer text", async () => {
    renderPage();

    await screen.findByLabelText("Your answer");
    fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "I went there and wrote my story." } });
    fireEvent.click(screen.getByRole("button", { name: "Submit to coach" }));

    await waitFor(() => {
      expect(mocks.homeworkSubmit).toHaveBeenCalledWith({
        homework_id: 12,
        answers: { response: "I went there and wrote my story." },
      });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Homework submitted");
    });
  });

  it("edits and deletes a homework card", async () => {
    renderPage();

    await screen.findByRole("button", { name: "Edit" });
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));

    const titleInput = screen.getByLabelText("Title");
    const promptInput = screen.getByLabelText("Prompt");
    fireEvent.change(titleInput, { target: { value: "Updated homework title" } });
    fireEvent.change(promptInput, { target: { value: "Updated prompt text" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "in_review" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(mocks.homeworkUpdate).toHaveBeenCalledWith(12, {
        title: "Updated homework title",
        tasks: [{ id: "response", type: "freeform", prompt: "Updated prompt text" }],
        due_at: null,
        status: "in_review",
      });
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Homework updated");
    });

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => {
      expect(mocks.homeworkDelete).toHaveBeenCalledWith(12);
      expect(mocks.pushToast).toHaveBeenCalledWith("success", "Homework deleted");
    });
  });
});
