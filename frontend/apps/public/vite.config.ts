import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Scaffolding — catálogo/cadastro/formulários/feedback são escopo da User Story 5.
export default defineConfig({
  plugins: [react()],
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
});
