/**
 * Notification Store
 *
 * M7-6: SSE Integration
 * Zustand store for managing real-time toast notifications.
 */

import { create } from "zustand";

// =============================================================================
// Types
// =============================================================================

export type NotificationType = "success" | "error" | "info" | "warning";

export interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  timestamp: number;
}

export interface NotificationInput {
  type: NotificationType;
  message: string;
}

interface NotificationState {
  notifications: Notification[];
  addNotification: (input: NotificationInput) => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

// =============================================================================
// Constants
// =============================================================================

/** Auto-dismiss timeout in milliseconds */
const AUTO_DISMISS_MS = 5000;

// =============================================================================
// Store
// =============================================================================

let _counter = 0;

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],

  addNotification: (input: NotificationInput) => {
    const id = `notif-${++_counter}-${Date.now()}`;
    const notification: Notification = {
      id,
      type: input.type,
      message: input.message,
      timestamp: Date.now(),
    };

    set((state) => ({
      notifications: [...state.notifications, notification],
    }));

    // Auto-dismiss after timeout
    setTimeout(() => {
      get().removeNotification(id);
    }, AUTO_DISMISS_MS);
  },

  removeNotification: (id: string) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    }));
  },

  clearAll: () => {
    set({ notifications: [] });
  },
}));
