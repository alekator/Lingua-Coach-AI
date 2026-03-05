import { describe, expect, it } from "vitest";
import type { AppBootstrapResponse } from "../api/types";
import { toBootstrapStorePayload } from "./workspace-context";

describe("workspace-context", () => {
  it("maps bootstrap payload to app store shape", () => {
    const bootstrap: AppBootstrapResponse = {
      user_id: 22,
      has_profile: true,
      needs_onboarding: false,
      next_step: "dashboard",
      owner_user_id: 1,
      active_workspace_id: 3,
      active_workspace_native_lang: "de",
      active_workspace_target_lang: "en",
      active_workspace_goal: "job interview",
    };

    expect(toBootstrapStorePayload(bootstrap)).toEqual({
      userId: 22,
      hasProfile: true,
      ownerUserId: 1,
      activeWorkspaceId: 3,
      activeWorkspaceNativeLang: "de",
      activeWorkspaceTargetLang: "en",
      activeWorkspaceGoal: "job interview",
    });
  });

  it("keeps nullable workspace fields as null", () => {
    const bootstrap: AppBootstrapResponse = {
      user_id: 1,
      has_profile: false,
      needs_onboarding: true,
      next_step: "onboarding",
      owner_user_id: 1,
      active_workspace_id: null,
      active_workspace_native_lang: null,
      active_workspace_target_lang: null,
      active_workspace_goal: null,
    };

    expect(toBootstrapStorePayload(bootstrap)).toEqual({
      userId: 1,
      hasProfile: false,
      ownerUserId: 1,
      activeWorkspaceId: null,
      activeWorkspaceNativeLang: null,
      activeWorkspaceTargetLang: null,
      activeWorkspaceGoal: null,
    });
  });
});
