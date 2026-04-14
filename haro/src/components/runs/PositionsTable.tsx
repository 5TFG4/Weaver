/**
 * PositionsTable Component
 *
 * Displays open positions with P&L coloring.
 */

import type { Position } from "../../api/types";

export interface PositionsTableProps {
  positions: Position[];
}

export function PositionsTable({ positions }: PositionsTableProps) {
  if (positions.length === 0) {
    return (
      <div data-testid="positions-empty" className="text-slate-400 text-sm">
        No open positions.
      </div>
    );
  }

  const columns = [
    { key: "symbol", label: "Symbol" },
    { key: "qty", label: "Qty" },
    { key: "side", label: "Side" },
    { key: "avg_entry_price", label: "Avg Entry" },
    { key: "market_value", label: "Market Value" },
    { key: "pnl", label: "Unrealized P&L" },
  ];

  return (
    <div data-testid="positions-table">
      <h3 className="text-lg font-semibold text-white mb-3">Open Positions</h3>
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead>
            <tr className="border-b border-slate-700">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3 text-slate-400 font-medium"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map((pos) => {
              const pnlNum = Number(pos.unrealized_pnl);
              const pnlColor = pnlNum >= 0 ? "text-green-400" : "text-red-400";

              return (
                <tr
                  key={pos.symbol}
                  className="border-b border-slate-700/50 hover:bg-slate-700/30"
                >
                  <td className="px-4 py-3 text-white font-medium">
                    {pos.symbol}
                  </td>
                  <td className="px-4 py-3 text-white">{pos.qty}</td>
                  <td className="px-4 py-3 text-white">{pos.side}</td>
                  <td className="px-4 py-3 text-white">
                    {pos.avg_entry_price}
                  </td>
                  <td className="px-4 py-3 text-white">{pos.market_value}</td>
                  <td
                    data-testid={`pnl-${pos.symbol}`}
                    className={`px-4 py-3 ${pnlColor}`}
                  >
                    {pos.unrealized_pnl} ({pos.unrealized_pnl_percent}%)
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
