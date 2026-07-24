import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Scaffolding — catálogo/cadastro/formulários/feedback são escopo da User Story 5.
//
// `base` é condicional ao modo de build (feature 186, US6): em produção este app é servido pelo
// MESMO serviço Railway do app interno, sob o prefixo `/catalogo/*` (ver `frontend/server.js`) —
// por isso os bundles/assets precisam ser referenciados com esse prefixo. Em dev (`npm run
// dev:public`) continua em `/`, preservando o proxy local e os testes Playwright já escritos
// (research.md §1).
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === "production" ? "/catalogo/" : "/",
  server: {
    port: 5175,
    proxy: {
      "/api": { target: "http://localhost:5000", changeOrigin: true },
      // Fotos do catálogo público são servidas por uma rota sem login (`/catalogo/midia/*`,
      // ver `app/catalogo/importer.py:_rewrite_public_url`) — sem isso, `assetUrl()` retorna um
      // caminho que o Vite dev server não sabe rotear (mesmo gap já corrigido em
      // apps/internal/vite.config.ts para `/uploads`, feature 182).
      "/catalogo/midia": { target: "http://localhost:5000", changeOrigin: true },
    },
  },
}));
