import { Link } from "react-router-dom";

export function RunsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Runs</h1>
          <p className="text-slate-400 mt-1">Manage trading runs</p>
        </div>
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors">
          + New Run
        </button>
      </div>

      {/* Runs Table */}
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
            {/* Empty state */}
            <tr>
              <td colSpan={6} className="px-6 py-12">
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
                  <p className="text-sm mt-1">
                    Create a new run to get started
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

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
