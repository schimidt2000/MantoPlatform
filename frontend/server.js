/**
 * Servidor estático único do monorepo `frontend/` (feature 186, US6; portal adicionado na 191).
 *
 * Substitui o `serve --single` anterior porque precisamos servir TRÊS SPAs a partir do mesmo
 * serviço Railway: `apps/internal/dist` (ERP, raiz), `apps/public/dist` (vitrine pública, sob
 * `/catalogo/*`) e `apps/portal/dist` (Portal do Artista, sob `/portal/*`). `serve --single` só
 * conhece um `index.html` de fallback — não dá para apontar três. `serve-handler` (biblioteca
 * por trás do `serve` que já rodava) é usado aqui de forma programática, uma vez por app, cada
 * um com seu próprio fallback de SPA — assim deep link/refresh funciona nos três (ex.:
 * `/portal/agenda` direto na barra de endereço).
 *
 * Requisições que começam com um prefixo montado são reescritas (prefixo removido de `req.url`)
 * antes de delegar ao `dist` correspondente — o prefixo só existe na URL pública, não na
 * estrutura de arquivos do build (o `base` do Vite cuida de gerar os links certos, ver
 * `apps/public/vite.config.ts` e `apps/portal/vite.config.ts`).
 *
 * Nota sobre `/portal`: o Flask também expõe `/portal/*` (Jinja legado), mas em outro serviço
 * e outro domínio — não há colisão. O portal React fala com o backend por `/api/portal/*`,
 * apontando para `VITE_API_BASE_URL`.
 */
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import handler from "serve-handler";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const INTERNAL_DIR = path.join(__dirname, "apps/internal/dist");
const PORT = process.env.PORT || 3000;

const SPA_REWRITE = [{ source: "**", destination: "/index.html" }];

/** Apps montados sob um prefixo de URL, avaliados na ordem antes do app da raiz. */
const MOUNTED_APPS = [
  { prefix: "/catalogo", dir: path.join(__dirname, "apps/public/dist") },
  { prefix: "/portal", dir: path.join(__dirname, "apps/portal/dist") },
];

/** True se a URL pertence ao prefixo montado (exato, com `/` ou com query). */
function matchesPrefix(url, prefix) {
  return url === prefix || url.startsWith(`${prefix}/`) || url.startsWith(`${prefix}?`);
}

const server = http.createServer((req, res) => {
  for (const { prefix, dir } of MOUNTED_APPS) {
    if (req.url && matchesPrefix(req.url, prefix)) {
      req.url = req.url.slice(prefix.length) || "/";
      return handler(req, res, { public: dir, rewrites: SPA_REWRITE, cleanUrls: false });
    }
  }
  return handler(req, res, { public: INTERNAL_DIR, rewrites: SPA_REWRITE, cleanUrls: false });
});

server.listen(PORT, () => {
  const mounts = MOUNTED_APPS.map(({ prefix }) => `${prefix}/*`).join(", ");
  console.log(`[server] apps/internal em / e apps montados em ${mounts} — porta ${PORT}`);
});
