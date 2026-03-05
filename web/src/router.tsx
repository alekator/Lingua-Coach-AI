import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api/client";
import { AppLayout } from "./components/layout";
import { DashboardPage } from "./pages/dashboard-page";
import { OnboardingPage } from "./pages/onboarding-page";
import { PlaceholderPage } from "./pages/placeholder-page";
import { useAppStore } from "./store/app-store";

function BootstrapGate() {
  const location = useLocation();
  const setBootstrapState = useAppStore((s) => s.setBootstrapState);
  const bootstrap = useQuery({
    queryKey: ["bootstrap"],
    queryFn: api.bootstrap,
  });

  useEffect(() => {
    if (!bootstrap.data) return;
    setBootstrapState({
      userId: bootstrap.data.user_id,
      hasProfile: bootstrap.data.has_profile,
    });
  }, [bootstrap.data, setBootstrapState]);

  if (bootstrap.isPending) {
    return <p className="centered">Loading app state...</p>;
  }
  if (bootstrap.isError) {
    return <p className="centered">Failed to load bootstrap state.</p>;
  }

  const needsOnboarding = bootstrap.data.needs_onboarding;
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
        <Route
          path="chat"
          element={<PlaceholderPage title="Chat" description="Teacher chat UI wiring goes here." />}
        />
        <Route
          path="voice"
          element={<PlaceholderPage title="Voice" description="Press-to-talk UI goes here." />}
        />
        <Route
          path="translate"
          element={<PlaceholderPage title="Translate" description="Translator page wiring goes here." />}
        />
        <Route
          path="vocab"
          element={<PlaceholderPage title="Vocab + SRS" description="Review queue UI goes here." />}
        />
        <Route
          path="grammar"
          element={<PlaceholderPage title="Grammar" description="Grammar analyzer UI goes here." />}
        />
        <Route
          path="homework"
          element={<PlaceholderPage title="Homework" description="Homework flow UI goes here." />}
        />
        <Route
          path="profile"
          element={<PlaceholderPage title="Profile & Skill Map" description="Analytics page goes here." />}
        />
      </Route>
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}

export function AppRouter() {
  return <BootstrapGate />;
}
