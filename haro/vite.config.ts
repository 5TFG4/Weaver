import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const defaultAllowedHosts = [
  "localhost",
  "127.0.0.1",
  "backend_dev",
  "frontend_dev",
];
const allowedHostsFromEnv = process.env.VITE_ALLOWED_HOSTS?.split(",")
  .map((host) => host.trim())
  .filter(Boolean);

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Port is handled by Docker port mapping (FRONTEND_PORT_DEV:5173)
    // Keep Vite on default 5173, Docker maps it to FRONTEND_PORT_DEV
    host: "0.0.0.0", // Allow access from outside container
    // Explicit allowlist to avoid disabling host header checks entirely.
    // Override with VITE_ALLOWED_HOSTS="host1,host2" when needed.
    allowedHosts: allowedHostsFromEnv?.length
      ? allowedHostsFromEnv
      : defaultAllowedHosts,
    proxy: {
      "/api": {
        target: process.env.API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
