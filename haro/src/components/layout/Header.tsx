import { Link } from "react-router-dom";
import { ConnectionStatus } from "../common/ConnectionStatus";

interface HeaderProps {
  isConnected?: boolean;
}

export function Header({ isConnected = false }: HeaderProps) {
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
          <ConnectionStatus isConnected={isConnected} />
        </div>
      </div>
    </header>
  );
}
