/**
 * Notification Store Tests
 *
 * M7-6: SSE Integration
 * TDD specs for Zustand notification store.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act } from "@testing-library/react";

// We'll test the store directly (no React rendering needed for Zustand)
import {
  useNotificationStore,
  type Notification,
} from "../../../src/stores/notificationStore";

describe("notificationStore", () => {
  beforeEach(() => {
    // Reset store state between tests
    useNotificationStore.getState().clearAll();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts with empty notifications", () => {
    const { notifications } = useNotificationStore.getState();
    expect(notifications).toEqual([]);
  });

  it("adds a notification", () => {
    const { addNotification } = useNotificationStore.getState();

    act(() => {
      addNotification({ type: "success", message: "Run started" });
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe("success");
    expect(notifications[0].message).toBe("Run started");
    expect(notifications[0].id).toBeDefined();
  });

  it("adds multiple notifications", () => {
    const { addNotification } = useNotificationStore.getState();

    act(() => {
      addNotification({ type: "success", message: "Order filled" });
      addNotification({ type: "error", message: "Connection lost" });
      addNotification({ type: "info", message: "Reconnecting..." });
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(3);
  });

  it("removes notification by id", () => {
    const { addNotification } = useNotificationStore.getState();

    act(() => {
      addNotification({ type: "success", message: "First" });
      addNotification({ type: "info", message: "Second" });
    });

    const id = useNotificationStore.getState().notifications[0].id;

    act(() => {
      useNotificationStore.getState().removeNotification(id);
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].message).toBe("Second");
  });

  it("auto-removes notification after timeout", () => {
    const { addNotification } = useNotificationStore.getState();

    act(() => {
      addNotification({ type: "success", message: "Temporary" });
    });

    expect(useNotificationStore.getState().notifications).toHaveLength(1);

    // Advance past the auto-dismiss timeout (5 seconds default)
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(useNotificationStore.getState().notifications).toHaveLength(0);
  });

  it("clears all notifications", () => {
    const { addNotification } = useNotificationStore.getState();

    act(() => {
      addNotification({ type: "success", message: "One" });
      addNotification({ type: "info", message: "Two" });
    });

    expect(useNotificationStore.getState().notifications).toHaveLength(2);

    act(() => {
      useNotificationStore.getState().clearAll();
    });

    expect(useNotificationStore.getState().notifications).toHaveLength(0);
  });
});
