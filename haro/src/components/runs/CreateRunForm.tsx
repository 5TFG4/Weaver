/**
 * CreateRunForm Component
 *
 * Modal form for creating a new trading run.
 * Collects strategy_id, mode, symbols, and optional config.
 */

import { useState } from "react";
import type { RunCreate, RunMode } from "../../api/types";

export interface CreateRunFormProps {
  onSubmit: (data: RunCreate) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function CreateRunForm({
  onSubmit,
  onCancel,
  isSubmitting = false,
}: CreateRunFormProps) {
  const [strategyId, setStrategyId] = useState("");
  const [mode, setMode] = useState<RunMode>("backtest");
  const [symbols, setSymbols] = useState("");
  const [timeframe, setTimeframe] = useState("1h");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const symbolList = symbols
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    onSubmit({
      strategy_id: strategyId,
      mode,
      symbols: symbolList,
      timeframe,
    });
  }

  return (
    <div
      data-testid="create-run-form"
      className="bg-slate-800 rounded-lg border border-slate-700 p-6"
    >
      <h2 className="text-lg font-semibold text-white mb-4">Create New Run</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="strategy-id"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Strategy
          </label>
          <input
            id="strategy-id"
            type="text"
            value={strategyId}
            onChange={(e) => setStrategyId(e.target.value)}
            placeholder="e.g. sma-crossover"
            required
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label
            htmlFor="run-mode"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Mode
          </label>
          <select
            id="run-mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as RunMode)}
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="backtest">Backtest</option>
            <option value="paper">Paper</option>
            <option value="live">Live</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="symbols"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Symbols
          </label>
          <input
            id="symbols"
            type="text"
            value={symbols}
            onChange={(e) => setSymbols(e.target.value)}
            placeholder="e.g. BTC/USD, ETH/USD"
            required
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label
            htmlFor="timeframe"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Timeframe
          </label>
          <select
            id="timeframe"
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="1m">1 Minute</option>
            <option value="5m">5 Minutes</option>
            <option value="15m">15 Minutes</option>
            <option value="1h">1 Hour</option>
            <option value="4h">4 Hours</option>
            <option value="1d">1 Day</option>
          </select>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm text-slate-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {isSubmitting ? "Creating..." : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}
