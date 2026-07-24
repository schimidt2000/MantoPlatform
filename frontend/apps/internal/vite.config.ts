import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// Proxy de dev: `/api/*`, `/uploads/*` e `/figurinos/<id>/print` vão para o Flask local
// (research.md §2). Evita CORS de cookie cross-origin em desenvolvimento — o browser trata as
// chamadas como same-origin. `/uploads` é necessário porque `assetUrl()` (@manto/api-client)
// devolve o path puro em dev, assumindo que o Vite roteia — sem esta entrada, qualquer preview de
// mídia enviada por upload (fotos de talento/figurino, catálogo, materiais de revisão) quebra no
// dev server (feature 182). A rota de impressão do Banco de Figurinos
// (`API_BASE + "/figurinos/<id>/print"`, feature 183) precisa do mesmo tratamento — mas o proxy
// usa um regex restrito a `/figurinos/<id>/print`, NUNCA `/figurinos` puro: a SPA também tem uma
// rota React Router em `/figurinos` (Banco de Figurinos) — um proxy amplo roubaria a navegação
// completa de página (deep link/refresh) para o Jinja legado em vez de servir o `index.html` da
// SPA.
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
      // Fotos do catálogo (Temas e Personagens, feature 185) são servidas por uma rota pública
      // separada de `/uploads` (`/catalogo/midia/*`, sem login — ver
      // `app/catalogo/importer.py:_rewrite_public_url`); mesmo gap do `/uploads` acima, mesma
      // correção.
      "/catalogo/midia": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
      "^/figurinos/\\d+/print$": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
