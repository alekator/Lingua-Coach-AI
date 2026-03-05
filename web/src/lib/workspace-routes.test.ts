import { beforeEach, describe, expect, it } from "vitest";
import { clearWorkspaceRoutes, getWorkspaceResumeRoute, rememberWorkspaceRoute } from "./workspace-routes";

describe("workspace-routes", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("stores and restores app routes per workspace", () => {
    rememberWorkspaceRoute(2, "/app/chat");
    expect(getWorkspaceResumeRoute(2)).toBe("/app/chat");
    expect(getWorkspaceResumeRoute(1)).toBeNull();
  });

  it("ignores non-app routes", () => {
    rememberWorkspaceRoute(2, "/");
    expect(getWorkspaceResumeRoute(2)).toBeNull();
  });

  it("clears remembered routes", () => {
    rememberWorkspaceRoute(2, "/app/chat");
    clearWorkspaceRoutes();
    expect(getWorkspaceResumeRoute(2)).toBeNull();
  });
});
