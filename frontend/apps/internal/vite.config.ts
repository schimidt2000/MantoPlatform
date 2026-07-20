import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// Proxy de dev: `/api/*` vai para o Flask local (research.md §2). Evita CORS de cookie
// cross-origin em desenvolvimento — o browser trata as chamadas como same-origin.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@manto/ui": fileURLToPath(new URL("../../packages/ui/src/index.ts", import.meta.url)),
      "@manto/money": fileURLToPath(
        new URL("../../packages/money/src/index.ts", import.meta.url),
      ),
      "@manto/api-client": fileURLToPath(
        new URL("../../packages/api-client/src/index.ts", import.meta.url),
      ),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
