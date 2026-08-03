import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "@/App";
import { configureOperatorSession } from "@/api/orchestrator";
import "@/index.css";
import "@/tokens/index";

const operatorSession = import.meta.env.VITE_OPERATOR_SESSION_TOKEN;
if (operatorSession) {
  configureOperatorSession(operatorSession);
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // TanStack Query owns backend snapshots — never invent data on the client, and never keep
      // a snapshot around indefinitely without knowing it may be stale.
      staleTime: 15_000,
      retry: 1,
    },
  },
});

const root = document.getElementById("root");
if (!root) {
  throw new Error("root element not found");
}

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
