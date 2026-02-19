/**
 * Toast Component Tests
 *
 * M7-6: SSE Integration
 * Tests for toast notification display + connection status indicator.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "../../../tests/utils";
import { Toast } from "../../../src/components/common/Toast";
import { ConnectionStatus } from "../../../src/components/common/ConnectionStatus";
import { useNotificationStore } from "../../../src/stores/notificationStore";

describe("Toast", () => {
  beforeEach(() => {
    useNotificationStore.getState().clearAll();
  });

  it("renders nothing when no notifications", () => {
    const { container } = render(<Toast />);
    expect(
      container.querySelector("[data-testid='toast-container']")?.children
        .length ?? 0,
    ).toBe(0);
  });

  it("renders notification messages", () => {
    act(() => {
      useNotificationStore.getState().addNotification({
        type: "success",
        message: "Run started successfully",
      });
    });

    render(<Toast />);
    expect(screen.getByText("Run started successfully")).toBeInTheDocument();
  });

  it("renders multiple notifications", () => {
    act(() => {
      useNotificationStore.getState().addNotification({
        type: "success",
        message: "First notification",
      });
      useNotificationStore.getState().addNotification({
        type: "error",
        message: "Second notification",
      });
    });

    render(<Toast />);
    expect(screen.getByText("First notification")).toBeInTheDocument();
    expect(screen.getByText("Second notification")).toBeInTheDocument();
  });

  it("can dismiss a notification via close button", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();

    act(() => {
      useNotificationStore.getState().addNotification({
        type: "info",
        message: "Dismissable notification",
      });
    });

    render(<Toast />);
    expect(screen.getByText("Dismissable notification")).toBeInTheDocument();

    const closeButton = screen.getByRole("button", { name: /dismiss/i });
    await user.click(closeButton);

    expect(
      screen.queryByText("Dismissable notification"),
    ).not.toBeInTheDocument();
  });
});

describe("ConnectionStatus", () => {
  it("renders connected state", () => {
    render(<ConnectionStatus isConnected={true} />);
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("renders disconnected state", () => {
    render(<ConnectionStatus isConnected={false} />);
    expect(screen.getByText("Disconnected")).toBeInTheDocument();
  });

  it("shows green indicator when connected", () => {
    const { container } = render(<ConnectionStatus isConnected={true} />);
    const dot = container.querySelector("[data-testid='connection-dot']");
    expect(dot?.className).toContain("bg-green");
  });

  it("shows red indicator when disconnected", () => {
    const { container } = render(<ConnectionStatus isConnected={false} />);
    const dot = container.querySelector("[data-testid='connection-dot']");
    expect(dot?.className).toContain("bg-red");
  });
});
