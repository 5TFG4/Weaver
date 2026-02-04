import { Link } from "react-router-dom";

export function Header() {
  return (
    <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">W</span>
          </div>
          <span className="text-xl font-semibold text-white">Weaver</span>
        </Link>
        <div className="flex items-center gap-4">
          <div className="text-sm text-slate-400">
            <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2"></span>
            Connected
          </div>
        </div>
      </div>
    </header>
  );
}
