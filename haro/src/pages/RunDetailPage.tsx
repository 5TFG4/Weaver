/**
 * RunDetailPage
 *
 * Displays detailed information about a single run.
 * For completed backtests, shows results: stats, equity curve, trade log.
 */

import { useParams, Link } from "react-router-dom";
import { useRun, useRunResults } from "../hooks/useRuns";
import { StatusBadge } from "../components/common/StatusBadge";
import { BacktestStatsCard } from "../components/runs/BacktestStatsCard";
import { EquityCurveChart } from "../components/runs/EquityCurveChart";
import { TradeLogTable } from "../components/runs/TradeLogTable";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const { data: run, isLoading, error } = useRun(runId ?? "");
  const {
    data: results,
    isLoading: resultsLoading,
  } = useRunResults(runId ?? "", {
    enabled: run?.status === "completed" && run?.mode === "backtest",
  });

  if (isLoading) {
    return (
      <div data-testid="run-detail-loading" className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-700 rounded w-1/3" />
          <div className="h-4 bg-slate-700 rounded w-1/2" />
        </div>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div data-testid="run-detail-error" className="p-6">
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
          <p className="text-red-400">
            {error?.message ?? "Run not found"}
          </p>
          <Link to="/runs" className="text-blue-400 hover:underline text-sm mt-2 inline-block">
            &larr; Back to Runs
          </Link>
        </div>
      </div>
    );
  }

  const showResults = run.status === "completed" && run.mode === "backtest";

  return (
    <div data-testid="run-detail" className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            to="/runs"
            className="text-blue-400 hover:underline text-sm mb-2 inline-block"
          >
            &larr; Back to Runs
          </Link>
          <h1 className="text-2xl font-bold text-white">
            Run {run.id.slice(0, 8)}
          </h1>
        </div>
        <StatusBadge variant={run.status} />
      </div>

      {/* Run Metadata */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-slate-400 text-xs">Strategy</p>
            <p className="text-white text-sm font-medium">{run.strategy_id}</p>
          </div>
          <div>
            <p className="text-slate-400 text-xs">Mode</p>
            <p className="text-white text-sm font-medium capitalize">{run.mode}</p>
          </div>
          <div>
            <p className="text-slate-400 text-xs">Created</p>
            <p className="text-white text-sm">{formatDate(run.created_at)}</p>
          </div>
          {run.started_at && (
            <div>
              <p className="text-slate-400 text-xs">Started</p>
              <p className="text-white text-sm">{formatDate(run.started_at)}</p>
            </div>
          )}
        </div>
        {run.error && (
          <div className="mt-4 bg-red-900/20 border border-red-700 rounded p-3">
            <p className="text-red-400 text-sm">{run.error}</p>
          </div>
        )}
      </div>

      {/* Backtest Results */}
      {showResults && resultsLoading && (
        <div data-testid="results-loading" className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-1/4" />
          <div className="h-48 bg-slate-700 rounded" />
        </div>
      )}

      {showResults && results && (
        <div className="space-y-6">
          <BacktestStatsCard result={results} />
          <EquityCurveChart data={results.equity_curve} />
          <TradeLogTable fills={results.fills} />
        </div>
      )}

      {run.status === "completed" && run.mode !== "backtest" && (
        <p className="text-slate-400 text-sm">
          Results are only available for backtest runs.
        </p>
      )}

      {run.status !== "completed" && (
        <p className="text-slate-400 text-sm">
          Results will appear here once the run completes.
        </p>
      )}
    </div>
  );
}
