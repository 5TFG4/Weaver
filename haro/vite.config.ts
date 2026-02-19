import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Port is handled by Docker port mapping (FRONTEND_PORT_DEV:5173)
    // Keep Vite on default 5173, Docker maps it to FRONTEND_PORT_DEV
    host: "0.0.0.0", // Allow access from outside container
    proxy: {
      "/api": {
        target: "http://backend_dev:8000",
        changeOrigin: true,
      },
    },
  },
});
