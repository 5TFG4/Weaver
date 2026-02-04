import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <div className="text-6xl font-bold text-slate-600 mb-4">404</div>
      <h1 className="text-2xl font-semibold text-white mb-2">Page Not Found</h1>
      <p className="text-slate-400 mb-6">
        The page you're looking for doesn't exist.
      </p>
      <Link
        to="/dashboard"
        className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
      >
        Go to Dashboard
      </Link>
    </div>
  );
}
