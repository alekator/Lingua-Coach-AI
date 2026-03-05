import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { getErrorMessage } from "../lib/errors";
import { languageLabelByCode } from "../lib/languages";
import { getWorkspaceResumeRoute } from "../lib/workspace-routes";
import { syncWorkspaceContext } from "../lib/workspace-context";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

export function WorkspaceSwitcher() {
  const activeWorkspaceId = useAppStore((s) => s.activeWorkspaceId);
  const setBootstrapState = useAppStore((s) => s.setBootstrapState);
  const pushToast = useToastStore((s) => s.push);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const workspaces = useQuery({
    queryKey: ["workspaces"],
    queryFn: api.workspacesList,
  });

  const switchWorkspace = useMutation({
    mutationFn: (workspaceId: number) => api.workspaceSwitch({ workspace_id: workspaceId }),
    onSuccess: async () => {
      const bootstrap = await syncWorkspaceContext(queryClient, setBootstrapState);
      if (bootstrap.needs_onboarding) {
        pushToast("info", "This learning space is new. Complete placement to start.");
        navigate("/", { replace: true });
        return;
      }
      if (bootstrap.active_workspace_id) {
        navigate(getWorkspaceResumeRoute(bootstrap.active_workspace_id) ?? "/app", { replace: true });
      }
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
