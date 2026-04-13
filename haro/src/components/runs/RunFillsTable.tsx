/**
 * RunFillsTable Component
 *
 * Displays fill history for a run with loading/error/empty states.
 */

import type { Fill } from "../../api/types";

export interface RunFillsTableProps {
  fills: Fill[];
  isLoading: boolean;
  isError: boolean;
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

export function RunFillsTable({
  fills,
  isLoading,
  isError,
}: RunFillsTableProps) {
  if (isLoading) {
    return (
      <div data-testid="fills-loading" className="animate-pulse space-y-2">
        <div className="h-6 bg-slate-700 rounded w-1/4" />
        <div className="h-32 bg-slate-700 rounded" />
      </div>
    );
  }

  if (isError) {
    return (
      <div
        data-testid="fills-error"
        className="bg-red-900/20 border border-red-700 rounded-lg p-4"
      >
        <p className="text-red-400 text-sm">Unable to load fills.</p>
      </div>
    );
  }

  if (fills.length === 0) {
    return (
      <div data-testid="fills-empty" className="text-slate-400 text-sm">
        No fills recorded yet.
      </div>
    );
  }

  const columns = [
    { key: "filled_at", label: "Time" },
    { key: "symbol", label: "Symbol" },
    { key: "side", label: "Side" },
    { key: "quantity", label: "Qty" },
    { key: "price", label: "Price" },
    { key: "commission", label: "Commission" },
  ];

  return (
    <div data-testid="fills-table">
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
            {fills.map((fill) => (
              <tr
                key={fill.id}
                className="border-b border-slate-700/50 hover:bg-slate-700/30"
              >
                <td className="px-4 py-3 text-white">
                  {formatTime(fill.filled_at)}
                </td>
                <td className="px-4 py-3 text-white">{fill.symbol ?? "—"}</td>
                <td className="px-4 py-3">
                  <span
                    className={
                      fill.side === "buy" ? "text-green-400" : "text-red-400"
                    }
                  >
                    {fill.side}
                  </span>
                </td>
                <td className="px-4 py-3 text-white">{fill.quantity}</td>
                <td className="px-4 py-3 text-white">{fill.price}</td>
                <td className="px-4 py-3 text-white">
                  {fill.commission ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
