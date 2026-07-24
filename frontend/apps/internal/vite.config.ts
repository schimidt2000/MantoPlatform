import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// Proxy de dev: `/api/*` e `/uploads/*` vão para o Flask local (research.md §2). Evita CORS de
// cookie cross-origin em desenvolvimento — o browser trata as chamadas como same-origin.
// `/uploads` é necessário porque `assetUrl()` (@manto/api-client) devolve o path puro em dev,
// assumindo que o Vite roteia — sem esta entrada, qualquer preview de mídia enviada por upload
// (fotos de talento/figurino, catálogo, materiais de revisão) quebra no dev server (feature 182).
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
      "/uploads": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
