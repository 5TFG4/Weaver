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
  RECONNECT_DELAY,
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

  it("reconnects after connection lost", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    expect(MockEventSource.instances).toHaveLength(1);

    // Simulate error → close
    act(() => {
      MockEventSource.latest().simulateError();
    });

    expect(MockEventSource.latest().readyState).toBe(MockEventSource.CLOSED);

    // Advance past reconnect delay
    act(() => {
      vi.advanceTimersByTime(RECONNECT_DELAY);
    });

    // A new EventSource should have been created
    expect(MockEventSource.instances).toHaveLength(2);
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
  // C-01: SSE event names must match backend PascalCase convention
  // Backend emits: run.Started, run.Stopped, run.Completed, run.Error
  // =========================================================================

  it("registers listeners with PascalCase run event names matching backend", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    const es = MockEventSource.latest();
    const registeredTypes = Array.from(
      (es as unknown as { listeners: Map<string, unknown[]> }).listeners.keys(),
    );

    // Must match backend RunEvents constants (PascalCase)
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
