import { describe, it, expect } from "vitest";
import { screen, render } from "@testing-library/react";
import App from "../../src/App";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { Dashboard } from "../../src/pages/Dashboard";
import { RunsPage } from "../../src/pages/RunsPage";
import { OrdersPage } from "../../src/pages/OrdersPage";
import { NotFound } from "../../src/pages/NotFound";
import { Layout } from "../../src/components/layout/Layout";

// Custom render with MemoryRouter for testing specific routes
function renderWithRouter(initialRoute: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Layout>
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/runs/:runId" element={<RunsPage />} />
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Layout>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App", () => {
  it("renders without crashing", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByText("Weaver")).toBeInTheDocument();
  });

  it("routes to dashboard by default", () => {
    renderWithRouter("/dashboard");
    expect(screen.getByText("System overview and status")).toBeInTheDocument();
  });

  it("routes to runs page on /runs", () => {
    renderWithRouter("/runs");
    expect(screen.getByText("Manage trading runs")).toBeInTheDocument();
  });

  it("routes to runs deep-link page on /runs/:runId", () => {
    renderWithRouter("/runs/run-2");
    expect(screen.getByText("Manage trading runs")).toBeInTheDocument();
  });

  it("routes to orders page on /orders", () => {
    renderWithRouter("/orders");
    expect(screen.getByText("View and manage orders")).toBeInTheDocument();
  });
});
