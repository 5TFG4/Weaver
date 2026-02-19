/**
 * Toast Component
 *
 * M7-6: SSE Integration
 * Renders notification toasts from the notification store.
 */

import {
  useNotificationStore,
  type NotificationType,
} from "../../stores/notificationStore";

// =============================================================================
// Style Helpers
// =============================================================================

const typeStyles: Record<NotificationType, string> = {
  success: "bg-green-800 border-green-600 text-green-100",
  error: "bg-red-800 border-red-600 text-red-100",
  warning: "bg-yellow-800 border-yellow-600 text-yellow-100",
  info: "bg-blue-800 border-blue-600 text-blue-100",
};

const typeIcons: Record<NotificationType, string> = {
  success: "✓",
  error: "✕",
  warning: "⚠",
  info: "ℹ",
};

// =============================================================================
// Component
// =============================================================================

export function Toast() {
  const notifications = useNotificationStore((s) => s.notifications);
  const removeNotification = useNotificationStore((s) => s.removeNotification);

  return (
    <div
      data-testid="toast-container"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
    >
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg ${typeStyles[notification.type]}`}
          role="alert"
        >
          <span className="text-lg">{typeIcons[notification.type]}</span>
          <span className="flex-1 text-sm">{notification.message}</span>
          <button
            onClick={() => removeNotification(notification.id)}
            className="text-current opacity-70 hover:opacity-100 ml-2"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
