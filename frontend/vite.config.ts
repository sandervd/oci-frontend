import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const base = process.env.VITE_BASE_PATH ?? "/";

export default defineConfig({
  plugins: [react()],
  base,
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.BACKEND_PROXY_TARGET ?? "http://localhost:8000",
      "/health": process.env.BACKEND_PROXY_TARGET ?? "http://localhost:8000"
    }
  }
});
