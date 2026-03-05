import { ApiError } from "../api/client";

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const rid = error.requestId ? ` (request ${error.requestId})` : "";
    return `HTTP ${error.status}: ${error.message}${rid}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error";
}
