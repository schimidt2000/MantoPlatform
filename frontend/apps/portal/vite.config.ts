import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// Proxy de dev: `/api`/`/portal`/`/uploads` vão para o Flask local — evita CORS de cookie
// cross-origin em desenvolvimento (mesmo padrão de apps/internal, feature 144 research.md §2).
// `/portal` é necessário aqui porque a foto de figurino é servida por
// `GET /portal/photo/<file>` (rota Jinja legada, checa a mesma sessão de talento).
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
    port: 5174,
    proxy: {
      "/api": { target: "http://localhost:5000", changeOrigin: true },
      "/portal": { target: "http://localhost:5000", changeOrigin: true },
      "/uploads": { target: "http://localhost:5000", changeOrigin: true },
    },
  },
});
