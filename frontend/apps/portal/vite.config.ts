import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// Proxy de dev: `/api`/`/portal`/`/uploads` vão para o Flask local — evita CORS de cookie
// cross-origin em desenvolvimento (mesmo padrão de apps/internal, feature 144 research.md §2).
// `/portal` é necessário aqui porque a foto de figurino é servida por
// `GET /portal/photo/<file>` (rota Jinja legada, checa a mesma sessão de talento).
//
// `base` é condicional ao modo (feature 191, mesmo padrão de apps/public): em produção este app
// é servido pelo MESMO serviço estático dos outros bundles, sob o prefixo `/portal/*` (ver
// `frontend/server.js`), então os assets precisam ser referenciados com esse prefixo e o React
// Router recebe o mesmo valor como `basename`. Em dev continua em `/`, preservando o proxy
// local — e é justamente por isso que o proxy de `/portal` acima NÃO conflita com as rotas do
// app: em dev o React vive na raiz, e só `/portal/photo/*` vai para o Flask.
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === "production" ? "/portal/" : "/",
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
      // Só a foto de figurino do Jinja legado — em dev o app React vive na raiz, então este
      // prefixo não sombreia nenhuma rota do portal novo.
      "/portal/photo": { target: "http://localhost:5000", changeOrigin: true },
      "/uploads": { target: "http://localhost:5000", changeOrigin: true },
    },
  },
}));
