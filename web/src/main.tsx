import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { ToastViewport } from "./components/toast-viewport";
import { registerPwaServiceWorker } from "./lib/pwa";
import { AppRouter } from "./router";
import { useAppStore } from "./store/app-store";
import "./styles.css";

const queryClient = new QueryClient();
const routerFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

void registerPwaServiceWorker();

function ThemeSync() {
  const theme = useAppStore((s) => s.theme);
  React.useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);
  return null;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeSync />
      <BrowserRouter future={routerFuture}>
        <AppRouter />
        <ToastViewport />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
