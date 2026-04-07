/**
 * EquityCurveChart Component
 *
 * Renders a time-series line chart of backtest equity using Recharts.
 */

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

export interface EquityCurveChartProps {
  data: Array<{ timestamp: string; equity: number }>;
}

function formatXTick(timestamp: string): string {
  const d = new Date(timestamp);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatYTick(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value}`;
}

export function EquityCurveChart({ data }: EquityCurveChartProps) {
  if (data.length === 0) {
    return (
      <div data-testid="equity-chart-empty" className="text-slate-400 text-sm">
        No equity data available.
      </div>
    );
  }

  return (
    <div data-testid="equity-chart">
      <h3 className="text-lg font-semibold text-white mb-3">Equity Curve</h3>
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatXTick}
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              tickFormatter={formatYTick}
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
              width={70}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "0.5rem",
                color: "#f8fafc",
              }}
              labelFormatter={(label) =>
                new Date(String(label)).toLocaleString()
              }
              formatter={(value) => [
                `$${Number(value).toLocaleString()}`,
                "Equity",
              ]}
            />
            <Line
              type="monotone"
              dataKey="equity"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
