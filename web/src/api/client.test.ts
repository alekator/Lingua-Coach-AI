import { api } from "./client";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("throws ApiError with parsed detail and request id from json body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        headers: {
          get: () => null,
        },
        text: async () => JSON.stringify({ detail: "bad request", request_id: "req-json" }),
      }),
    );

    await expect(api.progressSummary(1)).rejects.toEqual(
      expect.objectContaining({
        message: "bad request",
        status: 400,
        requestId: "req-json",
      }),
    );
  });

  it("falls back to plain text and header request id", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        headers: {
          get: (name: string) => (name === "X-Request-ID" ? "req-header" : null),
        },
        text: async () => "service unavailable",
      }),
    );

    await expect(api.progressSummary(1)).rejects.toEqual(
      expect.objectContaining({
        message: "service unavailable",
        status: 503,
        requestId: "req-header",
      }),
    );
  });
});
