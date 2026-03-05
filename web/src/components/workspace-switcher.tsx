import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { getErrorMessage } from "../lib/errors";
import { languageLabelByCode } from "../lib/languages";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function WorkspaceSwitcher() {
  const activeWorkspaceId = useAppStore((s) => s.activeWorkspaceId);
  const setBootstrapState = useAppStore((s) => s.setBootstrapState);
  const pushToast = useToastStore((s) => s.push);
  const queryClient = useQueryClient();
  const workspaces = useQuery({
    queryKey: ["workspaces"],
    queryFn: api.workspacesList,
  });

  const switchWorkspace = useMutation({
    mutationFn: (workspaceId: number) => api.workspaceSwitch({ workspace_id: workspaceId }),
    onSuccess: async () => {
      const bootstrap = await api.bootstrap();
      queryClient.setQueryData(["bootstrap"], bootstrap);
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      setBootstrapState({
        userId: bootstrap.user_id,
        hasProfile: bootstrap.has_profile,
        ownerUserId: bootstrap.owner_user_id,
        activeWorkspaceId: bootstrap.active_workspace_id ?? null,
        activeWorkspaceNativeLang: bootstrap.active_workspace_native_lang ?? null,
        activeWorkspaceTargetLang: bootstrap.active_workspace_target_lang ?? null,
        activeWorkspaceGoal: bootstrap.active_workspace_goal ?? null,
      });
      pushToast("success", "Learning space switched");
    },
    onError: (err) => {
      pushToast("error", getErrorMessage(err));
    },
  });

  const items = Array.isArray(workspaces.data?.items) ? workspaces.data.items : [];
  if (workspaces.isPending || workspaces.isError || items.length === 0) {
    return null;
  }

  return (
    <label>
      Space
      <select
        value={activeWorkspaceId ?? workspaces.data?.active_workspace_id ?? ""}
        onChange={(e) => switchWorkspace.mutate(Number(e.target.value))}
        disabled={switchWorkspace.isPending}
      >
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {languageLabelByCode(item.native_lang)} {"->"} {languageLabelByCode(item.target_lang)}
          </option>
        ))}
      </select>
    </label>
  );
}
