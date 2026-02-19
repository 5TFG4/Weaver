/**
 * Dashboard Page
 *
 * System overview showing active runs, total orders,
 * API health status, and recent activity feed.
 * Consumes data via TanStack Query hooks.
 */

import { Link } from "react-router-dom";
import { useRuns } from "../hooks/useRuns";
import { useOrders } from "../hooks/useOrders";
import { useHealth } from "../hooks/useHealth";
import { StatCard } from "../components/common/StatCard";
import { ActivityFeed } from "../components/dashboard/ActivityFeed";

export function Dashboard() {
  const runsQuery = useRuns({ page: 1, page_size: 50 });
  const ordersQuery = useOrders({ page: 1, page_size: 1 });
  const healthQuery = useHealth();

  const isLoading =
    runsQuery.isLoading || ordersQuery.isLoading || healthQuery.isLoading;
  const isError = runsQuery.isError;

  if (isError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 mt-1">System overview and status</p>
        </div>
        <div
          data-testid="dashboard-error"
          className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400"
        >
          <p className="font-medium">Failed to load dashboard data</p>
          <p className="text-sm mt-1">
            {runsQuery.error?.message ?? "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div data-testid="dashboard-loading" className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 mt-1">System overview and status</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-slate-800 rounded-lg p-6 border border-slate-700 h-24 animate-pulse"
            />
          ))}
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 h-48 animate-pulse" />
      </div>
    );
  }

  const runs = runsQuery.data?.items ?? [];
  const activeRunCount = runs.filter((r) => r.status === "running").length;
  const totalRuns = runsQuery.data?.total ?? 0;
  const totalOrders = ordersQuery.data?.total ?? 0;
  const healthStatus = healthQuery.data?.status === "ok" ? "Online" : "Offline";
  const healthColor: "success" | "error" =
    healthQuery.data?.status === "ok" ? "success" : "error";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-400 mt-1">System overview and status</p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard
          title="Active Runs"
          value={String(activeRunCount)}
          icon={
            <svg
              className="w-6 h-6 text-blue-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          }
        />
        <StatCard
          title="Total Runs"
          value={String(totalRuns)}
          icon={
            <svg
              className="w-6 h-6 text-purple-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 10h16M4 14h16M4 18h16"
              />
            </svg>
          }
        />
        <StatCard
          title="Total Orders"
          value={String(totalOrders)}
          icon={
            <svg
              className="w-6 h-6 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
          }
        />
        <StatCard
          title="API Status"
          value={healthStatus}
          status={healthColor}
          icon={
            <div
              className={`w-3 h-3 rounded-full ${healthColor === "success" ? "bg-green-500 animate-pulse" : "bg-red-500"}`}
            />
          }
        />
      </div>

      {/* Recent Activity */}
      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Recent Activity</h2>
          <Link
            to="/runs"
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            View All →
          </Link>
        </div>
        <div className="p-4">
          <ActivityFeed runs={runs.slice(0, 5)} />
        </div>
      </div>
    </div>
  );
}
