/**
 * RunsPage
 *
 * Displays a paginated list of trading runs with status badges,
 * start/stop controls, and a form to create new runs.
 * Consumes data via TanStack Query hooks.
 */

import { useState } from "react";
import { Link } from "react-router-dom";
import { useRuns, useCreateRun, useStopRun } from "../hooks/useRuns";
import { StatusBadge } from "../components/common/StatusBadge";
import { CreateRunForm } from "../components/runs/CreateRunForm";
import type { Run, RunCreate, RunMode } from "../api/types";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

/** Determine if a run can be stopped */
function canStop(status: string): boolean {
  return status === "running" || status === "pending";
}

export function RunsPage() {
  const [showForm, setShowForm] = useState(false);
  const runsQuery = useRuns({ page: 1, page_size: 50 });
  const createRunMutation = useCreateRun();
  const stopRunMutation = useStopRun();

  // Track locally-stopped run IDs for optimistic UI update
  const [stoppedIds, setStoppedIds] = useState<Set<string>>(new Set());

  const isLoading = runsQuery.isLoading;
  const isError = runsQuery.isError;

  function handleCreate(data: RunCreate) {
    createRunMutation.mutate(data, {
      onSuccess: () => {
        setShowForm(false);
      },
    });
  }

  function handleStop(runId: string) {
    stopRunMutation.mutate(runId, {
      onSuccess: () => {
        setStoppedIds((prev) => new Set(prev).add(runId));
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Error State
  // ---------------------------------------------------------------------------
  if (isError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Runs</h1>
          <p className="text-slate-400 mt-1">Manage trading runs</p>
        </div>
        <div
          data-testid="runs-error"
          className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400"
        >
          <p className="font-medium">Failed to load runs</p>
          <p className="text-sm mt-1">
            {runsQuery.error?.message ?? "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Loading State
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div data-testid="runs-loading" className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Runs</h1>
          <p className="text-slate-400 mt-1">Manage trading runs</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-12 bg-slate-700/50 rounded animate-pulse"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Data State
  // ---------------------------------------------------------------------------
  const runs = runsQuery.data?.items ?? [];

  /** Get effective status considering optimistic stop updates */
  function effectiveStatus(run: Run): string {
    return stoppedIds.has(run.id) ? "stopped" : run.status;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Runs</h1>
          <p className="text-slate-400 mt-1">Manage trading runs</p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
        >
          + New Run
        </button>
      </div>

      {/* Create Run Form */}
      {showForm && (
        <CreateRunForm
          onSubmit={handleCreate}
          onCancel={() => setShowForm(false)}
          isSubmitting={createRunMutation.isPending}
        />
      )}

      {/* Runs Table */}
      {runs.length === 0 ? (
        <div
          data-testid="runs-empty"
          className="bg-slate-800 rounded-lg border border-slate-700 p-12"
        >
          <div className="text-center text-slate-400">
            <svg
              className="w-12 h-12 mx-auto mb-4 text-slate-600"
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
            <p>No runs yet</p>
            <p className="text-sm mt-1">Create a new run to get started</p>
          </div>
        </div>
      ) : (
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-700/50">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                  Run ID
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                  Strategy
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                  Symbols
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                  Mode
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                  Status
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                  Created
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {runs.map((run) => {
                const status = effectiveStatus(run);
                return (
                  <tr
                    key={run.id}
                    data-testid={`run-row-${run.id}`}
                    className="hover:bg-slate-700/30 transition-colors"
                  >
                    <td className="px-6 py-4 text-sm text-slate-200 font-mono">
                      {run.id}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-200">
                      {run.strategy_id}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-200">
                      {run.symbols.join(", ")}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={run.mode as RunMode} />
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={status as Run["status"]} />
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-400">
                      {formatDate(run.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      {canStop(status) && (
                        <button
                          onClick={() => handleStop(run.id)}
                          className="text-sm text-red-400 hover:text-red-300 font-medium transition-colors"
                        >
                          Stop
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Quick Links */}
      <div className="flex gap-4">
        <Link
          to="/orders"
          className="text-blue-400 hover:text-blue-300 text-sm"
        >
          View all orders →
        </Link>
      </div>
    </div>
  );
}
