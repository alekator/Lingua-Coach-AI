import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { ToastViewport } from "./components/toast-viewport";
import { AppRouter } from "./router";
import "./styles.css";

const queryClient = new QueryClient();
const routerFuture = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={routerFuture}>
        <AppRouter />
        <ToastViewport />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
