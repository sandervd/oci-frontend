import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const base = process.env.VITE_BASE_PATH ?? "/";
const allowedHosts = (process.env.VITE_ALLOWED_HOSTS ?? "localhost,127.0.0.1")
  .split(",")
  .map((host) => host.trim())
  .filter(Boolean);

export default defineConfig({
  plugins: [react()],
  base,
  server: {
    port: 5173,
    allowedHosts,
    proxy: {
      [`${base.replace(/\/$/, "")}/api`]: {
        target: process.env.BACKEND_PROXY_TARGET ?? "http://localhost:8000",
        rewrite: (path) => path.replace(new RegExp(`^${base.replace(/\/$/, "")}/api`), "/api")
      },
      "/api": process.env.BACKEND_PROXY_TARGET ?? "http://localhost:8000",
      "/health": process.env.BACKEND_PROXY_TARGET ?? "http://localhost:8000"
    }
  }
});
