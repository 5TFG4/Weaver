/**
 * BacktestStatsCard Component
 *
 * Displays key backtest statistics in a grid of stat cards.
 */

import type { BacktestResult } from "../../api/types";

export interface BacktestStatsCardProps {
  result: BacktestResult;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${minutes}m ${secs}s`;
}

function formatPercent(value: unknown): string {
  if (typeof value !== "number") return "—";
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: unknown): string {
  if (typeof value !== "number") return "—";
  return value.toFixed(2);
}

export function BacktestStatsCard({ result }: BacktestStatsCardProps) {
  const { stats } = result;

  const items = [
    {
      label: "Final Equity",
      value: `$${Number(result.final_equity).toLocaleString()}`,
    },
    { label: "Total Return", value: formatPercent(stats.total_return) },
    { label: "Sharpe Ratio", value: formatNumber(stats.sharpe_ratio) },
    { label: "Max Drawdown", value: formatPercent(stats.max_drawdown) },
    { label: "Total Trades", value: String(stats.total_trades ?? "—") },
    { label: "Win Rate", value: formatPercent(stats.win_rate) },
    {
      label: "Bars Processed",
      value: result.total_bars_processed.toLocaleString(),
    },
    { label: "Duration", value: formatDuration(result.simulation_duration_ms) },
  ];

  return (
    <div data-testid="backtest-stats">
      <h3 className="text-lg font-semibold text-white mb-3">Statistics</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {items.map((item) => (
          <div
            key={item.label}
            className="bg-slate-800 rounded-lg p-4 border border-slate-700"
          >
            <p className="text-slate-400 text-xs">{item.label}</p>
            <p className="text-white text-lg font-semibold mt-1">
              {item.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
