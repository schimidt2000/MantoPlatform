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
 * ── Proxy reverso para o Flask (consolidação do React como interface primária) ────────────────
 * Este serviço agora é a ÚNICA porta de entrada da plataforma (`app.mantoproducoes.com.br`):
 * antes de qualquer SPA, as rotas que ainda pertencem ao backend são repassadas ao Flask. Os
 * filtros espelham os proxies de dev do Vite — o que funciona em `npm run dev:*` passa a
 * funcionar igual em produção, sem `VITE_API_BASE_URL` cross-origin e sem cookie de terceiro:
 *
 *   - `/api/*`              → API JSON (todas as chamadas do `@manto/api-client`)
 *   - `/uploads/*`          → mídia salva por `app/storage.py` (`assetUrl()` devolve esse path)
 *   - `/catalogo/midia/*`   → fotos públicas do catálogo (rota sem login, ver
 *                             `app/catalogo/importer.py:_rewrite_public_url`) — precisa vir ANTES
 *                             do mount `/catalogo`, senão a SPA pública engole a imagem
 *   - `/portal/photo/*`     → foto de figurino do portal (rota Jinja legada que checa a sessão do
 *                             talento; `GET /api/portal/events/<id>/figurino` devolve esse path) —
 *                             precisa vir ANTES do mount `/portal` pelo mesmo motivo
 *   - `/figurinos/<id>/print` → ficha de impressão, único Jinja que a SPA interna ainda linka.
 *                               Regex restrito ao sub-path: `/figurinos` puro é rota do React
 *                               Router (Banco de Figurinos) e um proxy amplo roubaria o deep link.
 */
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import handler from "serve-handler";
import httpProxy from "http-proxy";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const INTERNAL_DIR = path.join(__dirname, "apps/internal/dist");
const PORT = process.env.PORT || 3000;

/**
 * Normaliza a origem do Flask vinda de `BACKEND_URL`.
 *
 * Sem isto, um valor sem esquema (ex.: `mantoplatform.railway.internal`, que é como o painel do
 * Railway mostra o domínio privado) **derruba o processo**: `http-proxy` chama `requires-port`
 * com `protocol === null` e estoura `TypeError` de forma **síncrona**, dentro de `proxy.web` —
 * antes de qualquer callback de erro. O resultado em produção é o pior possível de diagnosticar:
 * a página abre normalmente e só as chamadas de API matam o servidor, uma a uma.
 *
 * O esquema é deduzido do host: rede privada do Railway, `localhost` e IP falam HTTP; o resto é
 * domínio público, que fala HTTPS.
 */
function resolveBackendUrl(raw) {
  const value = (raw ?? "").trim();
  if (!value) return "http://localhost:5000";

  let candidate = value;
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(candidate)) {
    const host = candidate.split("/")[0].split(":")[0];
    const isLocal =
      host === "localhost" || host.endsWith(".railway.internal") || /^[\d.]+$/.test(host);
    candidate = `${isLocal ? "http" : "https"}://${candidate}`;
    console.warn(
      `[server] BACKEND_URL="${value}" veio sem esquema — assumindo "${candidate}". ` +
        `Defina o esquema explicitamente na variável do serviço.`,
    );
  }

  try {
    const parsed = new URL(candidate);
    if (!parsed.hostname) throw new Error("sem host");
    return candidate.replace(/\/+$/, "");
  } catch {
    console.error(
      `[server] BACKEND_URL="${value}" é inválida — o proxy vai responder 502. ` +
        `Use algo como "https://<servico>.up.railway.app".`,
    );
    return null;
  }
}

/** Origem do Flask. Em produção, definir `BACKEND_URL` nas variáveis do serviço no Railway. */
const BACKEND_URL = resolveBackendUrl(process.env.BACKEND_URL);

/**
 * `changeOrigin: true` reescreve o `Host` para o do backend — mesmo ajuste dos três
 * `vite.config.ts`. Não é cosmético: com `BACKEND_URL` apontando para um domínio público do
 * Railway, preservar o `Host` original (`app.mantoproducoes.com.br`) faria o roteador de borda
 * devolver a requisição para ESTE serviço, em laço. `xfwd` envia os `X-Forwarded-*` para o Flask
 * enxergar o cliente original.
 */
const proxy = httpProxy.createProxyServer({ changeOrigin: true, xfwd: true });

const SPA_REWRITE = [{ source: "**", destination: "/index.html" }];

/** Apps montados sob um prefixo de URL, avaliados na ordem antes do app da raiz. */
const MOUNTED_APPS = [
  { prefix: "/catalogo", dir: path.join(__dirname, "apps/public/dist") },
  { prefix: "/portal", dir: path.join(__dirname, "apps/portal/dist") },
];

/**
 * Prefixos repassados ao Flask, avaliados antes de qualquer SPA.
 *
 * `/google` é o par connect/callback do OAuth do Google Calendar
 * (`app/calendar/routes.py`). Não é mídia nem API, mas precisa estar aqui: o `redirect_uri`
 * registrado no Google Console é um endereço fixo e, apontando para este domínio, o browser
 * volta do consentimento direto no fallback de SPA — a reconexão da agenda quebraria em
 * silêncio. Não há rota `/google` no React Router, então não sombreia nada.
 */
const BACKEND_PREFIXES = ["/api", "/uploads", "/catalogo/midia", "/portal/photo", "/google"];

/** Rotas Jinja remanescentes, casadas por regex para não sombrear rotas do React Router. */
const BACKEND_PATTERNS = [/^\/figurinos\/\d+\/print(?:[/?]|$)/];

/** True se a URL pertence ao prefixo montado (exato, com `/` ou com query). */
function matchesPrefix(url, prefix) {
  return url === prefix || url.startsWith(`${prefix}/`) || url.startsWith(`${prefix}?`);
}

/** True se a requisição é do backend Flask e não de um dos bundles SPA. */
function isBackendRequest(url) {
  return (
    BACKEND_PREFIXES.some((prefix) => matchesPrefix(url, prefix)) ||
    BACKEND_PATTERNS.some((pattern) => pattern.test(url))
  );
}

const server = http.createServer((req, res) => {
  // Regras de proxy para o backend Flask — antes dos SPAs, senão o fallback de `/catalogo` e
  // `/portal` devolveria `index.html` no lugar da mídia.
  if (req.url && isBackendRequest(req.url)) {
    /** Responde 502 sem derrubar o processo. `headersSent` cobre falha no meio do streaming. */
    const badGateway = (err) => {
      console.error(`[proxy] ${req.method} ${req.url} → ${BACKEND_URL}: ${err.message}`);
      if (res.headersSent) {
        res.destroy();
        return;
      }
      res.statusCode = 502;
      res.setHeader("content-type", "text/plain; charset=utf-8");
      res.end("Bad Gateway");
    };

    if (!BACKEND_URL) {
      badGateway(new Error("BACKEND_URL ausente ou inválida"));
      return;
    }
    // O try/catch não é decorativo: `proxy.web` estoura de forma SÍNCRONA para alvo malformado,
    // fora do callback de erro. Sem ele, a exceção sobe como uncaught e mata o servidor inteiro —
    // os três SPAs junto com o proxy.
    try {
      proxy.web(req, res, { target: BACKEND_URL }, badGateway);
    } catch (err) {
      badGateway(err);
    }
    return;
  }

  // Fallback existente para os bundles SPA (público, portal, interno).
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
  console.log(
    BACKEND_URL
      ? `[server] proxy para ${BACKEND_URL}: ${BACKEND_PREFIXES.join(", ")}, /figurinos/<id>/print`
      : `[server] SEM BACKEND_URL válida — ${BACKEND_PREFIXES.join(", ")} e /figurinos/<id>/print responderão 502`,
  );
});
