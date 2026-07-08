import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Backend al que el dev server proxya /api, /ws y /health.
// Por defecto 127.0.0.1:8000 (backend local / docker). Override con VITE_BACKEND_URL.
// Se usa 127.0.0.1 en vez de 'localhost' para evitar que Node resuelva a IPv6
// (::1) y falle con ECONNREFUSED cuando el backend escucha solo en IPv4.
const backend = process.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": backend,
      "/ws": { target: backend.replace(/^http/, "ws"), ws: true },
      "/health": backend,
    },
  },
  build: { outdir: "dist" },
});
