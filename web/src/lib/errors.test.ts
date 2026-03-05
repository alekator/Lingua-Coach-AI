import { ApiError } from "../api/client";
import { getErrorMessage } from "./errors";

describe("getErrorMessage", () => {
  it("formats api errors with request id", () => {
    const error = new ApiError("invalid payload", 422, "req-123");
    expect(getErrorMessage(error)).toBe("HTTP 422: invalid payload (request req-123)");
  });

  it("formats api errors without request id", () => {
    const error = new ApiError("not found", 404);
    expect(getErrorMessage(error)).toBe("HTTP 404: not found");
  });

  it("falls back to standard errors", () => {
    expect(getErrorMessage(new Error("boom"))).toBe("boom");
  });

  it("handles non-error values", () => {
    expect(getErrorMessage("bad")).toBe("Unknown error");
  });
});
