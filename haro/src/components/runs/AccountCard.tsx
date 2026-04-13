/**
 * AccountCard Component
 *
 * Displays account snapshot: portfolio value, buying power, cash, status.
 */

import type { AccountInfo } from "../../api/types";

export interface AccountCardProps {
  account: AccountInfo | null;
  isLoading: boolean;
}

function formatCurrency(value: string): string {
  return `$${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function AccountCard({ account, isLoading }: AccountCardProps) {
  if (isLoading) {
    return (
      <div data-testid="account-card-loading" className="animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-1/4 mb-3" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="bg-slate-800 rounded-lg p-4 border border-slate-700"
            >
              <div className="h-3 bg-slate-700 rounded w-1/2 mb-2" />
              <div className="h-5 bg-slate-700 rounded w-3/4" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!account) return null;

  const items = [
    {
      label: "Portfolio Value",
      value: formatCurrency(account.portfolio_value),
    },
    { label: "Buying Power", value: formatCurrency(account.buying_power) },
    { label: "Cash", value: formatCurrency(account.cash) },
    { label: "Status", value: account.status },
  ];

  return (
    <div data-testid="account-card">
      <h3 className="text-lg font-semibold text-white mb-3">Account</h3>
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
