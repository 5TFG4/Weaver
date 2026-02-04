export function OrdersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Orders</h1>
          <p className="text-slate-400 mt-1">View and manage orders</p>
        </div>
        <div className="flex gap-2">
          <select className="bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm">
            <option value="">All Runs</option>
          </select>
          <select className="bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm">
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="filled">Filled</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-700/50">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                Order ID
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                Symbol
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                Side
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                Type
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                Qty
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                Price
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                Status
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                Time
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {/* Empty state */}
            <tr>
              <td colSpan={8} className="px-6 py-12">
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
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                  <p>No orders yet</p>
                  <p className="text-sm mt-1">
                    Orders will appear here when strategies generate trades
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
