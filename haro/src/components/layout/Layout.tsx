import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

interface LayoutProps {
  children: React.ReactNode;
  isConnected?: boolean;
}

export function Layout({ children, isConnected = false }: LayoutProps) {
  return (
    <div className="flex flex-col h-screen bg-slate-900">
      <Header isConnected={isConnected} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
