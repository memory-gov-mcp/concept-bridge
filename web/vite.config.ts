import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: { rollupOptions: { output: { manualChunks: { cytoscape: ["cytoscape"] } } } },
  server: {
    host: "127.0.0.1",
    port: mode === "mock" ? 5174 : 5173,
    strictPort: true,
    fs: {
      allow: [
        fileURLToPath(new URL(".", import.meta.url)),
        fileURLToPath(new URL("../fixtures/bridge.sample.json", import.meta.url)),
        fileURLToPath(new URL("../eval/reports/latest.json", import.meta.url)),
      ],
    },
    proxy: mode === "mock" ? undefined : { "/api/v1": "http://127.0.0.1:8000" },
  },
}));
