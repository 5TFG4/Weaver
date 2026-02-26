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

// =============================================================================
// Constants
// =============================================================================

export const SSE_ENDPOINT = "/api/v1/events/stream";
export const RECONNECT_DELAY = 3000;

// =============================================================================
// Hook
// =============================================================================

export function useSSE() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const connect = () => {
      // Close any existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const eventSource = new EventSource(SSE_ENDPOINT);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
      };

      eventSource.onerror = () => {
        eventSource.close();
        setIsConnected(false);

        // Schedule reconnect
        reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
      };

      // =========================================================================
      // Run Events
      // =========================================================================

      eventSource.addEventListener("run.Started", (e: MessageEvent) => {
        const data = JSON.parse(e.data);
        queryClient.invalidateQueries({ queryKey: ["runs"] });
        addNotification({
          type: "success",
          message: `Run ${data.run_id} started`,
        });
      });

      eventSource.addEventListener("run.Stopped", (e: MessageEvent) => {
        const data = JSON.parse(e.data);
        queryClient.invalidateQueries({ queryKey: ["runs"] });
        addNotification({
          type: "info",
          message: `Run ${data.run_id} stopped`,
        });
      });

      eventSource.addEventListener("run.Completed", (e: MessageEvent) => {
        const data = JSON.parse(e.data);
        queryClient.invalidateQueries({ queryKey: ["runs"] });
        addNotification({
          type: "success",
          message: `Run ${data.run_id} completed`,
        });
      });

      eventSource.addEventListener("run.Error", (e: MessageEvent) => {
        const data = JSON.parse(e.data);
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
        const data = JSON.parse(e.data);
        queryClient.invalidateQueries({ queryKey: ["orders"] });
        addNotification({
          type: "info",
          message: `Order ${data.order_id} created`,
        });
      });

      eventSource.addEventListener("orders.Filled", () => {
        queryClient.invalidateQueries({ queryKey: ["orders"] });
        addNotification({
          type: "success",
          message: `Order filled`,
        });
      });

      eventSource.addEventListener("orders.Rejected", (e: MessageEvent) => {
        const data = JSON.parse(e.data);
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
        const data = JSON.parse(e.data);
        queryClient.invalidateQueries({ queryKey: ["orders"] });
        addNotification({
          type: "info",
          message: `Order ${data.order_id} cancelled`,
        });
      });
    };

    connect();

    return () => {
      eventSourceRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [queryClient, addNotification]);

  return { isConnected };
}
