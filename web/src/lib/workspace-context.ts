import type { Query, QueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { AppBootstrapResponse } from "../api/types";

type BootstrapStorePayload = {
  userId: number;
  hasProfile: boolean;
  ownerUserId?: number | null;
  activeWorkspaceId?: number | null;
  activeWorkspaceNativeLang?: string | null;
  activeWorkspaceTargetLang?: string | null;
  activeWorkspaceGoal?: string | null;
};

export function toBootstrapStorePayload(bootstrap: AppBootstrapResponse): BootstrapStorePayload {
  return {
    userId: bootstrap.user_id,
    hasProfile: bootstrap.has_profile,
    ownerUserId: bootstrap.owner_user_id,
    activeWorkspaceId: bootstrap.active_workspace_id ?? null,
    activeWorkspaceNativeLang: bootstrap.active_workspace_native_lang ?? null,
    activeWorkspaceTargetLang: bootstrap.active_workspace_target_lang ?? null,
    activeWorkspaceGoal: bootstrap.active_workspace_goal ?? null,
  };
}

function isWorkspaceContextQuery(query: Query): boolean {
  return query.queryKey[0] !== "bootstrap";
}

export async function syncWorkspaceContext(
  queryClient: QueryClient,
  setBootstrapState: (payload: BootstrapStorePayload) => void,
): Promise<AppBootstrapResponse> {
  const bootstrap = await api.bootstrap();
  queryClient.setQueryData(["bootstrap"], bootstrap);
  setBootstrapState(toBootstrapStorePayload(bootstrap));
  await queryClient.invalidateQueries({
    predicate: isWorkspaceContextQuery,
  });
  return bootstrap;
}
