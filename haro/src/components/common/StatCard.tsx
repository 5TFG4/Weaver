/**
 * StatCard Component
 *
 * Reusable card for displaying a single statistic with optional
 * icon, trend indicator, and status color.
 */

import type { ReactNode } from "react";

export interface StatCardProps {
  title: string;
  value: string;
  icon?: ReactNode;
  trend?: string;
  status?: "default" | "success" | "warning" | "error";
}

const statusColors: Record<string, string> = {
  default: "text-white",
  success: "text-green-400",
  warning: "text-yellow-400",
  error: "text-red-400",
};

export function StatCard({
  title,
  value,
  icon,
  trend,
  status = "default",
}: StatCardProps) {
  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-slate-400 text-sm">{title}</p>
          <p className={`text-3xl font-bold mt-1 ${statusColors[status]}`}>
            {value}
          </p>
          {trend && <p className="text-sm text-slate-400 mt-1">{trend}</p>}
        </div>
        {icon && (
          <div className="w-12 h-12 bg-slate-700/50 rounded-lg flex items-center justify-center">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
