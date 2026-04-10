/**
 * useSSE Hook Tests
 *
 * M7-6: SSE Integration
 * Tests for SSE connection hook with auto-reconnection and
 * React Query cache invalidation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useSSE,
  SSE_ENDPOINT,
  DISCONNECT_GRACE_MS,
} from "../../../src/hooks/useSSE";
import { useNotificationStore } from "../../../src/stores/notificationStore";
import type { ReactNode } from "react";

// =============================================================================
// EventSource Mock
// =============================================================================

type EventSourceListener = (event: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];

  url: string;
  readyState: number = 0; // CONNECTING
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  private listeners: Map<string, EventSourceListener[]> = new Map();

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventSourceListener) {
    const existing = this.listeners.get(type) || [];
    existing.push(listener);
    this.listeners.set(type, existing);
  }

  removeEventListener(type: string, listener: EventSourceListener) {
    const existing = this.listeners.get(type) || [];
    this.listeners.set(
      type,
      existing.filter((l) => l !== listener),
    );
  }

  close() {
    this.readyState = MockEventSource.CLOSED;
  }

  // Test helpers
  simulateOpen() {
    this.readyState = MockEventSource.OPEN;
    this.onopen?.();
  }

  simulateError() {
    this.onerror?.();
  }

  simulateEvent(type: string, data: unknown) {
    const event = new MessageEvent(type, {
      data: JSON.stringify(data),
    });
    const listeners = this.listeners.get(type) || [];
    listeners.forEach((l) => l(event));
  }

  /** Send raw string data (for testing malformed JSON handling) */
  simulateRawEvent(type: string, rawData: string) {
    const event = new MessageEvent(type, { data: rawData });
    const listeners = this.listeners.get(type) || [];
    listeners.forEach((l) => l(event));
  }

  static reset() {
    MockEventSource.instances = [];
  }

  static latest(): MockEventSource {
    return MockEventSource.instances[MockEventSource.instances.length - 1];
  }
}

// =============================================================================
// Setup
// =============================================================================

// Replace global EventSource
const OriginalEventSource = globalThis.EventSource;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useSSE", () => {
  beforeEach(() => {
    MockEventSource.reset();
    globalThis.EventSource = MockEventSource as unknown as typeof EventSource;
    useNotificationStore.getState().clearAll();
    vi.useFakeTimers();
  });

  afterEach(() => {
    globalThis.EventSource = OriginalEventSource;
    vi.useRealTimers();
  });

  it("connects to SSE endpoint on mount", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.latest().url).toBe(SSE_ENDPOINT);
  });

  it("reports connected status after open", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSSE(), { wrapper });

    expect(result.current.isConnected).toBe(false);

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    expect(result.current.isConnected).toBe(true);
  });

  it("does not close EventSource on error (native reconnect)", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    expect(MockEventSource.instances).toHaveLength(1);

    // Simulate error — should NOT close the connection
    act(() => {
      MockEventSource.latest().simulateError();
    });

    // readyState should NOT be CLOSED (browser handles reconnect natively)
    expect(MockEventSource.latest().readyState).not.toBe(
      MockEventSource.CLOSED,
    );
    // No new instance created — we trust the browser
    expect(MockEventSource.instances).toHaveLength(1);
  });

  it("delays disconnect indicator by grace period", () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });
    expect(result.current.isConnected).toBe(true);

    // Error fires but grace period protects
    act(() => {
      MockEventSource.latest().simulateError();
    });
    expect(result.current.isConnected).toBe(true);

    // Still connected before grace period expires
    act(() => {
      vi.advanceTimersByTime(DISCONNECT_GRACE_MS - 1);
    });
    expect(result.current.isConnected).toBe(true);

    // After grace period expires → disconnected
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current.isConnected).toBe(false);
  });

  it("cancels disconnect indicator when reconnected within grace period", () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    // Error → start grace timer
    act(() => {
      MockEventSource.latest().simulateError();
    });

    // Reconnect before grace period
    act(() => {
      vi.advanceTimersByTime(2000);
      MockEventSource.latest().simulateOpen();
    });

    // Advance past original grace period — should still be connected
    act(() => {
      vi.advanceTimersByTime(DISCONNECT_GRACE_MS);
    });
    expect(result.current.isConnected).toBe(true);
  });

  it("calls onEvent callback for run.Started event", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    act(() => {
      MockEventSource.latest().simulateEvent("run.Started", {
        run_id: "run-123",
      });
    });

    // Should add a notification
    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe("success");
    expect(notifications[0].message).toContain("run-123");
  });

  it("calls onEvent callback for orders.Filled event", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    act(() => {
      MockEventSource.latest().simulateEvent("orders.Filled", {
        order_id: "order-456",
      });
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe("success");
    expect(notifications[0].message).toContain("filled");
  });

  it("invalidates React Query cache on run events", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const WrapperWithSpy = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    renderHook(() => useSSE(), { wrapper: WrapperWithSpy });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    act(() => {
      MockEventSource.latest().simulateEvent("run.Started", {
        run_id: "run-1",
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["runs"] }),
    );
  });

  it("cleans up EventSource on unmount", () => {
    const wrapper = createWrapper();
    const { unmount } = renderHook(() => useSSE(), { wrapper });

    const es = MockEventSource.latest();
    expect(es.readyState).not.toBe(MockEventSource.CLOSED);

    unmount();

    expect(es.readyState).toBe(MockEventSource.CLOSED);
  });

  it("handles run.Stopped event", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
      MockEventSource.latest().simulateEvent("run.Stopped", {
        run_id: "run-789",
      });
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe("info");
    expect(notifications[0].message).toContain("run-789");
  });

  it("handles orders.Rejected event", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
      MockEventSource.latest().simulateEvent("orders.Rejected", {
        order_id: "order-999",
        reason: "Insufficient funds",
      });
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe("error");
    expect(notifications[0].message).toContain("rejected");
  });

  it("handles orders.Rejected event with reject_reason payload", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
      MockEventSource.latest().simulateEvent("orders.Rejected", {
        order_id: "order-1000",
        reject_reason: "Exchange rejected order",
      });
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe("error");
    expect(notifications[0].message).toContain("Exchange rejected order");
  });

  // =========================================================================
  // M-03: orders.Cancelled listener
  // =========================================================================

  it("handles orders.Cancelled event", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
      MockEventSource.latest().simulateEvent("orders.Cancelled", {
        order_id: "order-777",
      });
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe("info");
    expect(notifications[0].message).toContain("cancelled");
  });

  // =========================================================================
  // H1: SSE Safety — safeParse protection against malformed JSON
  // =========================================================================

  it("does not crash when SSE event has malformed JSON data", () => {
    const wrapper = createWrapper();
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    // Malformed JSON must NOT throw
    expect(() => {
      act(() => {
        MockEventSource.latest().simulateRawEvent(
          "run.Started",
          "NOT VALID JSON{{{",
        );
      });
    }).not.toThrow();

    // Should log a warning
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining("[SSE]"),
      expect.anything(),
    );

    // Should NOT produce a notification (event is silently skipped)
    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(0);

    consoleSpy.mockRestore();
  });

  it("does not crash when orders.Rejected has malformed JSON", () => {
    const wrapper = createWrapper();
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    renderHook(() => useSSE(), { wrapper });
    act(() => MockEventSource.latest().simulateOpen());

    expect(() => {
      act(() => {
        MockEventSource.latest().simulateRawEvent(
          "orders.Rejected",
          "<html>502 Bad Gateway</html>",
        );
      });
    }).not.toThrow();

    expect(consoleSpy).toHaveBeenCalled();
    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(0);

    consoleSpy.mockRestore();
  });

  it("still processes valid JSON normally after safeParse", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    act(() => MockEventSource.latest().simulateOpen());
    act(() => {
      MockEventSource.latest().simulateEvent("run.Completed", {
        run_id: "run-safe-1",
      });
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].message).toContain("run-safe-1");
  });

  // =========================================================================
  // M14-11: run.Created SSE listener
  // =========================================================================

  it("handles run.Created event with query invalidation and notification", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const WrapperWithSpy = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    renderHook(() => useSSE(), { wrapper: WrapperWithSpy });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    act(() => {
      MockEventSource.latest().simulateEvent("run.Created", {
        run_id: "new-run-42",
        strategy_id: "sma-crossover",
        mode: "paper",
        status: "pending",
      });
    });

    // Should invalidate runs query
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["runs"] }),
    );

    // Should add a notification
    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe("info");
    expect(notifications[0].message).toContain("new-run-42");
  });

  // =========================================================================
  // C-01: SSE event names must match backend PascalCase convention
  // Backend emits: run.Created, run.Started, run.Stopped, run.Completed, run.Error
  // =========================================================================

  it("registers listeners with PascalCase run event names matching backend", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    const es = MockEventSource.latest();
    const registeredTypes = Array.from(
      (es as unknown as { listeners: Map<string, unknown[]> }).listeners.keys(),
    );

    // Must match backend RunEvents constants (PascalCase)
    expect(registeredTypes).toContain("run.Created");
    expect(registeredTypes).toContain("run.Started");
    expect(registeredTypes).toContain("run.Stopped");
    expect(registeredTypes).toContain("run.Completed");
    expect(registeredTypes).toContain("run.Error");

    // Must NOT have lowercase variants
    expect(registeredTypes).not.toContain("run.started");
    expect(registeredTypes).not.toContain("run.stopped");
    expect(registeredTypes).not.toContain("run.completed");
    expect(registeredTypes).not.toContain("run.error");
  });
});
