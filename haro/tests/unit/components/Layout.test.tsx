import { describe, it, expect } from "vitest";
import { screen, render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Layout } from "../../../src/components/layout/Layout";

// Helper to render with router
function renderWithRouter(ui: React.ReactElement, initialRoute = "/") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>{ui}</MemoryRouter>,
  );
}

describe("Layout", () => {
  it("renders header with app name", () => {
    renderWithRouter(
      <Layout>
        <div>content</div>
      </Layout>,
    );
    expect(screen.getByText("Weaver")).toBeInTheDocument();
  });

  it("renders sidebar with navigation links", () => {
    renderWithRouter(
      <Layout>
        <div>content</div>
      </Layout>,
    );
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Runs")).toBeInTheDocument();
    expect(screen.getByText("Orders")).toBeInTheDocument();
  });

  it("renders children in main content area", () => {
    renderWithRouter(
      <Layout>
        <div data-testid="test-child">Test Content</div>
      </Layout>,
    );
    expect(screen.getByTestId("test-child")).toBeInTheDocument();
    expect(screen.getByText("Test Content")).toBeInTheDocument();
  });

  it("highlights active navigation link", () => {
    // Navigate to /dashboard to activate the link
    renderWithRouter(
      <Layout>
        <div>content</div>
      </Layout>,
      "/dashboard",
    );
    const dashboardLink = screen.getByText("Dashboard").closest("a");
    // The link should have the active state class (bg-blue-600)
    expect(dashboardLink).toHaveClass("bg-blue-600");
  });
});
