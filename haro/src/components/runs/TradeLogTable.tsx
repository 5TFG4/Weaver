/**
 * TradeLogTable Component
 *
 * Displays a table of simulated fills from a backtest result.
 */

export interface TradeLogTableProps {
  fills: Array<Record<string, unknown>>;
}

function formatValue(val: unknown): string {
  if (val == null) return "—";
  if (typeof val === "number") return val.toLocaleString();
  return String(val);
}

export function TradeLogTable({ fills }: TradeLogTableProps) {
  if (fills.length === 0) {
    return (
      <div data-testid="trade-log-empty" className="text-slate-400 text-sm">
        No trades recorded.
      </div>
    );
  }

  const columns = [
    { key: "timestamp", label: "Time" },
    { key: "symbol", label: "Symbol" },
    { key: "side", label: "Side" },
    { key: "qty", label: "Qty" },
    { key: "fill_price", label: "Price" },
    { key: "commission", label: "Commission" },
    { key: "slippage", label: "Slippage" },
  ];

  return (
    <div data-testid="trade-log">
      <h3 className="text-lg font-semibold text-white mb-3">Trade Log</h3>
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
            {fills.map((fill, idx) => (
              <tr
                key={idx}
                className="border-b border-slate-700/50 hover:bg-slate-700/30"
              >
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3 text-white">
                    {col.key === "side" ? (
                      <span
                        className={
                          String(fill[col.key]).toLowerCase() === "buy"
                            ? "text-green-400"
                            : "text-red-400"
                        }
                      >
                        {formatValue(fill[col.key])}
                      </span>
                    ) : (
                      formatValue(fill[col.key])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
