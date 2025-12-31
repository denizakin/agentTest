import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "./styles.css";

const queryClient = new QueryClient();

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root container missing");
}

createRoot(container).render(
  <MantineProvider withGlobalStyles withNormalizeCSS>
    <Notifications position="top-right" />
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </MantineProvider>
);
