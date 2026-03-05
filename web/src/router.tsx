import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api/client";
import { AppLayout } from "./components/layout";
import { rememberWorkspaceRoute } from "./lib/workspace-routes";
import { toBootstrapStorePayload } from "./lib/workspace-context";
import { ChatPage } from "./pages/chat-page";
import { DashboardPage } from "./pages/dashboard-page";
import { ExercisesPage } from "./pages/exercises-page";
import { GrammarPage } from "./pages/grammar-page";
import { HomeworkPage } from "./pages/homework-page";
import { OnboardingPage } from "./pages/onboarding-page";
import { ProfilePage } from "./pages/profile-page";
import { ScenariosPage } from "./pages/scenarios-page";
import { SessionPage } from "./pages/session-page";
import { TranslatePage } from "./pages/translate-page";
import { VocabPage } from "./pages/vocab-page";
import { VoicePage } from "./pages/voice-page";
import { useAppStore } from "./store/app-store";

function BootstrapGate() {
  const location = useLocation();
  const hasProfile = useAppStore((s) => s.hasProfile);
  const activeWorkspaceId = useAppStore((s) => s.activeWorkspaceId);
  const setBootstrapState = useAppStore((s) => s.setBootstrapState);
  const bootstrap = useQuery({
    queryKey: ["bootstrap"],
    queryFn: api.bootstrap,
  });

  useEffect(() => {
    if (!bootstrap.data) return;
    setBootstrapState(toBootstrapStorePayload(bootstrap.data));
  }, [bootstrap.data, setBootstrapState]);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    rememberWorkspaceRoute(activeWorkspaceId, location.pathname);
  }, [activeWorkspaceId, location.pathname]);

  if (bootstrap.isPending) {
    return <p className="centered">Loading app state...</p>;
  }
  if (bootstrap.isError) {
    return <p className="centered">Failed to load bootstrap state.</p>;
  }

  const needsOnboarding = bootstrap.data.needs_onboarding && !hasProfile;
  if (needsOnboarding && location.pathname !== "/") {
    return <Navigate to="/" replace />;
  }
  if (!needsOnboarding && location.pathname === "/") {
    return <Navigate to="/app" replace />;
  }
  return <RoutesMap />;
}

function RoutesMap() {
  return (
    <Routes>
      <Route path="/" element={<OnboardingPage />} />
      <Route path="/app" element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="session" element={<SessionPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="voice" element={<VoicePage />} />
        <Route path="translate" element={<TranslatePage />} />
        <Route path="exercises" element={<ExercisesPage />} />
        <Route path="scenarios" element={<ScenariosPage />} />
        <Route path="vocab" element={<VocabPage />} />
        <Route path="grammar" element={<GrammarPage />} />
        <Route path="homework" element={<HomeworkPage />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}

export function AppRouter() {
  return <BootstrapGate />;
}
