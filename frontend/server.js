/**
 * Servidor estático único do monorepo `frontend/` (feature 186, US6).
 *
 * Substitui o `serve --single` anterior porque agora precisamos servir DOIS SPAs a partir do
 * mesmo serviço Railway: `apps/internal/dist` (ERP, raiz) e `apps/public/dist` (vitrine pública,
 * sob o prefixo `/catalogo/*`). `serve --single` só conhece um `index.html` de fallback — não dá
 * para apontar dois. `serve-handler` (biblioteca por trás do `serve` que já rodava) é usado aqui
 * de forma programática, uma vez por app, cada um com seu próprio fallback de SPA — assim deep
 * link/refresh funciona nos dois (ex.: `/catalogo/algum-slug` direto na barra de endereço).
 *
 * Requisições que começam com `/catalogo` são reescritas (prefixo removido de `req.url`) antes
 * de delegar a `apps/public/dist` — o prefixo só existe na URL pública, não na estrutura de
 * arquivos do build (o `base` do Vite cuida de gerar os links certos, ver
 * `apps/public/vite.config.ts`).
 */
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import handler from "serve-handler";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const INTERNAL_DIR = path.join(__dirname, "apps/internal/dist");
const PUBLIC_DIR = path.join(__dirname, "apps/public/dist");
const PORT = process.env.PORT || 3000;

const SPA_REWRITE = [{ source: "**", destination: "/index.html" }];

const server = http.createServer((req, res) => {
  if (req.url === "/catalogo" || req.url?.startsWith("/catalogo/") || req.url?.startsWith("/catalogo?")) {
    req.url = req.url.replace(/^\/catalogo/, "") || "/";
    return handler(req, res, { public: PUBLIC_DIR, rewrites: SPA_REWRITE, cleanUrls: false });
  }
  return handler(req, res, { public: INTERNAL_DIR, rewrites: SPA_REWRITE, cleanUrls: false });
});

server.listen(PORT, () => {
  console.log(`[server] apps/internal em / e apps/public em /catalogo/* — porta ${PORT}`);
});
