/**
 * useSSE Hook
 *
 * M7-6: SSE Integration
 * Connects to the backend SSE endpoint for real-time event streaming.
 * Features:
 * - Auto-reconnection on connection loss
 * - React Query cache invalidation on relevant events
 * - Toast notifications for important events
 * - Connection status tracking
 */

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNotificationStore } from "../stores/notificationStore";
import { accountKeys } from "./useAccount";
import { fillKeys } from "./useFills";

// =============================================================================
// Constants
// =============================================================================

export const SSE_ENDPOINT = "/api/v1/events/stream";

/** Grace period (ms) before showing "Disconnected" — avoids flicker on reload */
export const DISCONNECT_GRACE_MS = 5000;

// =============================================================================
// Utilities
// =============================================================================

function safeParse(raw: string): Record<string, unknown> | null {
  try {
    return JSON.parse(raw);
  } catch {
    console.warn("[SSE] Failed to parse event data:", raw);
    return null;
  }
}

// =============================================================================
// Hook
// =============================================================================

export function useSSE() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);
  const eventSourceRef = useRef<EventSource | null>(null);
  const disconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const eventSource = new EventSource(SSE_ENDPOINT);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      // Clear any pending disconnect indicator
      if (disconnectTimerRef.current) {
        clearTimeout(disconnectTimerRef.current);
        disconnectTimerRef.current = null;
      }
      setIsConnected(true);
    };

    eventSource.onerror = () => {
      // Browser will auto-reconnect (spec §9.2.3); do NOT call .close().
      // Show "Disconnected" only after a grace period so brief
      // reconnects (e.g. backend reload) don't flash the indicator.
      if (!disconnectTimerRef.current) {
        disconnectTimerRef.current = setTimeout(() => {
          setIsConnected(false);
          disconnectTimerRef.current = null;
        }, DISCONNECT_GRACE_MS);
      }
    };

    // =========================================================================
    // Run Events
    // =========================================================================

    eventSource.addEventListener("run.Started", (e: MessageEvent) => {
      const data = safeParse(e.data);
      if (!data) return;
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      addNotification({
        type: "success",
        message: `Run ${data.run_id} started`,
      });
    });

    eventSource.addEventListener("run.Stopped", (e: MessageEvent) => {
      const data = safeParse(e.data);
      if (!data) return;
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      addNotification({
        type: "info",
        message: `Run ${data.run_id} stopped`,
      });
    });

    eventSource.addEventListener("run.Completed", (e: MessageEvent) => {
      const data = safeParse(e.data);
      if (!data) return;
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      addNotification({
        type: "success",
        message: `Run ${data.run_id} completed`,
      });
    });

    eventSource.addEventListener("run.Created", (e: MessageEvent) => {
      const data = safeParse(e.data);
      if (!data) return;
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      addNotification({
        type: "info",
        message: `Run ${data.run_id} created`,
      });
    });

    eventSource.addEventListener("run.Error", (e: MessageEvent) => {
      const data = safeParse(e.data);
      if (!data) return;
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      addNotification({
        type: "error",
        message: `Run ${data.run_id} error: ${data.error}`,
      });
    });

    // =========================================================================
    // Order Events
    // =========================================================================

    eventSource.addEventListener("orders.Created", (e: MessageEvent) => {
      const data = safeParse(e.data);
      if (!data) return;
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      addNotification({
        type: "info",
        message: `Order ${data.order_id} created`,
      });
    });

    eventSource.addEventListener(
      "orders.PartiallyFilled",
      (e: MessageEvent) => {
        const data = safeParse(e.data);
        queryClient.invalidateQueries({ queryKey: ["orders"] });
        queryClient.invalidateQueries({ queryKey: fillKeys.all });
        queryClient.invalidateQueries({ queryKey: accountKeys.all });
        addNotification({
          type: "info",
          message: data?.symbol
            ? `Partial fill: ${data.symbol}`
            : "Order partially filled",
        });
      },
    );

    eventSource.addEventListener("orders.Filled", (e: MessageEvent) => {
      const data = safeParse(e.data);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: fillKeys.all });
      queryClient.invalidateQueries({ queryKey: accountKeys.all });
      addNotification({
        type: "success",
        message: data?.symbol ? `Order filled: ${data.symbol}` : "Order filled",
      });
    });

    eventSource.addEventListener("orders.Rejected", (e: MessageEvent) => {
      const data = safeParse(e.data);
      if (!data) return;
      const rejectReason =
        data.reject_reason ??
        data.reason ??
        data.error_message ??
        "Unknown reason";
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      addNotification({
        type: "error",
        message: `Order rejected: ${rejectReason}`,
      });
    });

    eventSource.addEventListener("orders.Cancelled", (e: MessageEvent) => {
      const data = safeParse(e.data);
      if (!data) return;
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      addNotification({
        type: "info",
        message: `Order ${data.order_id} cancelled`,
      });
    });

    return () => {
      eventSourceRef.current?.close();
      if (disconnectTimerRef.current) {
        clearTimeout(disconnectTimerRef.current);
      }
    };
  }, [queryClient, addNotification]);

  return { isConnected };
}
