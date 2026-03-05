const STORAGE_KEY = "linguacoach.workspace.last-route.v1";

type WorkspaceRouteMap = Record<string, string>;

function readRoutes(): WorkspaceRouteMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as WorkspaceRouteMap;
  } catch {
    return {};
  }
}

function writeRoutes(routes: WorkspaceRouteMap): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(routes));
}

function isAppRoute(pathname: string): boolean {
  return pathname === "/app" || pathname.startsWith("/app/");
}

export function rememberWorkspaceRoute(workspaceId: number, pathname: string): void {
  if (!Number.isInteger(workspaceId) || workspaceId <= 0) return;
  if (!isAppRoute(pathname)) return;
  const current = readRoutes();
  current[String(workspaceId)] = pathname;
  writeRoutes(current);
}

export function getWorkspaceResumeRoute(workspaceId: number): string | null {
  if (!Number.isInteger(workspaceId) || workspaceId <= 0) return null;
  const current = readRoutes();
  const pathname = current[String(workspaceId)];
  if (typeof pathname !== "string" || !isAppRoute(pathname)) return null;
  return pathname;
}
