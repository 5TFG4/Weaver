import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { Dashboard } from "./pages/Dashboard";
import { RunsPage } from "./pages/RunsPage";
import { OrdersPage } from "./pages/OrdersPage";
import { NotFound } from "./pages/NotFound";
import { Toast } from "./components/common/Toast";
import { useSSE } from "./hooks/useSSE";

function App() {
  const { isConnected } = useSSE();

  return (
    <>
      <Layout isConnected={isConnected}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
      <Toast />
    </>
  );
}

export default App;
