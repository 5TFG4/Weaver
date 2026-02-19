/**
 * ActivityFeed Component
 *
 * Displays a list of recent runs with status badges.
 */

import { Link } from "react-router-dom";
import type { Run } from "../../api/types";

export interface ActivityFeedProps {
  runs: Run[];
  isLoading?: boolean;
}

const statusConfig: Record<
  string,
  { color: string; bgColor: string; label: string }
> = {
  running: {
    color: "text-green-400",
    bgColor: "bg-green-500/20",
    label: "Running",
  },
  completed: {
    color: "text-blue-400",
    bgColor: "bg-blue-500/20",
    label: "Completed",
  },
  stopped: {
    color: "text-yellow-400",
    bgColor: "bg-yellow-500/20",
    label: "Stopped",
  },
  pending: {
    color: "text-slate-400",
    bgColor: "bg-slate-500/20",
    label: "Pending",
  },
  error: {
    color: "text-red-400",
    bgColor: "bg-red-500/20",
    label: "Error",
  },
};

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMs / 3_600_000);
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export function ActivityFeed({ runs, isLoading }: ActivityFeedProps) {
  if (isLoading) {
    return (
      <div data-testid="activity-loading" className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-slate-700/50 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        <p>No recent activity</p>
        <p className="text-sm mt-1">
          Events will appear here when runs are active
        </p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-slate-700">
      {runs.map((run) => {
        const config = statusConfig[run.status] ?? statusConfig.pending;
        return (
          <div
            key={run.id}
            className="flex items-center justify-between py-3 px-2"
          >
            <div className="flex items-center gap-3">
              <span
                className={`inline-block w-2 h-2 rounded-full ${config.color.replace("text-", "bg-")}`}
              />
              <div>
                <span className="text-sm text-white">{run.strategy_id}</span>
                <span className="text-xs text-slate-500 ml-2">
                  {run.symbols.join(", ")}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`text-xs px-2 py-0.5 rounded ${config.bgColor} ${config.color}`}
              >
                {config.label}
              </span>
              <span className="text-xs text-slate-500">
                {formatTimeAgo(run.created_at)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
