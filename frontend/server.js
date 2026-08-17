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
import fs from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import handler from "serve-handler";
import httpProxy from "http-proxy";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const INTERNAL_DIR = path.join(__dirname, "apps/internal/dist");
const PUBLIC_DIST = path.join(__dirname, "apps/public/dist");
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

/**
 * Cache do navegador — o contrato padrão de SPA com assets versionados por hash.
 *
 * Sem isto o `serve-handler` não manda `Cache-Control` nenhum, e aí o navegador aplica cache
 * heurístico em cima do `Last-Modified`: **o `index.html` fica guardado** e continua apontando
 * para o bundle da versão anterior. O deploy sobe, a verificação em produção passa (o servidor
 * já entrega o arquivo novo) e mesmo assim o usuário segue rodando o JavaScript velho até dar
 * um refresh forçado. Foi assim que uma tela do catálogo apareceu sem um botão que já estava
 * publicado havia horas.
 *
 * - `index.html` (e qualquer HTML): `no-cache` = pode guardar, mas **revalida sempre** antes de
 *   usar. O arquivo tem menos de 1 KB e vira 304 quando nada mudou.
 * - `assets/*`: o nome já carrega o hash do conteúdo, então mudou o conteúdo = mudou a URL.
 *   Pode ser `immutable` por um ano com segurança.
 *
 * A regra de `assets` vem DEPOIS de propósito: o `serve-handler` percorre a lista inteira e a
 * última que casar vence.
 */
const CACHE_HEADERS = [
  { source: "**", headers: [{ key: "Cache-Control", value: "no-cache" }] },
  {
    source: "assets/**",
    headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
  },
];

/** Opções do `serve-handler` compartilhadas pelos três apps. */
const SERVE_OPTIONS = { rewrites: SPA_REWRITE, cleanUrls: false, headers: CACHE_HEADERS };

/** Apps montados sob um prefixo de URL, avaliados na ordem antes do app da raiz. */
const MOUNTED_APPS = [
  { prefix: "/catalogo", dir: PUBLIC_DIST },
  { prefix: "/portal", dir: path.join(__dirname, "apps/portal/dist") },
];

/**
 * Hosts dedicados ao Portal do Artista, onde a raiz é o portal e não o ERP interno.
 *
 * Sem isto, apontar `portal.mantoproducoes.com.br` para este serviço entrega
 * `apps/internal/dist` — o talento cairia na tela de login do staff. Espelha o
 * `portal_domain_routing` que o Flask já tinha para o mesmo host.
 */
const PORTAL_HOSTS = new Set(
  (process.env.PORTAL_HOSTS ?? "portal.mantoproducoes.com.br")
    .split(",")
    .map((host) => host.trim().toLowerCase())
    .filter(Boolean),
);

/**
 * Hosts dedicados à Loja de Interações Virtuais, onde a raiz é a campanha (feature 224d).
 *
 * `alo.mantoproducoes.com.br/<slug>` é o endereço que vai em story e link de bio — sem isto a
 * família teria que digitar `app.mantoproducoes.com.br/catalogo/v/<slug>`, que além de feio
 * expõe o ERP. Mesmo arranjo de `PORTAL_HOSTS`: um redirect que leva o caminho para dentro do
 * mount da SPA pública.
 */
const ALO_HOSTS = new Set(
  (process.env.ALO_HOSTS ?? "alo.mantoproducoes.com.br")
    .split(",")
    .map((host) => host.trim().toLowerCase())
    .filter(Boolean),
);

/**
 * Prefixos repassados ao Flask, avaliados antes de qualquer SPA.
 *
 * `/google` é o par connect/callback do OAuth do Google Calendar
 * (`app/calendar/routes.py`). Não é mídia nem API, mas precisa estar aqui: o `redirect_uri`
 * registrado no Google Console é um endereço fixo e, apontando para este domínio, o browser
 * volta do consentimento direto no fallback de SPA — a reconexão da agenda quebraria em
 * silêncio. Não há rota `/google` no React Router, então não sombreia nada.
 *
 * SUPERFÍCIES PÚBLICAS POR LINK (Jinja, sem login) — os links já distribuídos apontam para
 * este domínio e, sem estas entradas, caíam no fallback do ERP interno, que PEDE LOGIN:
 *   - `/avaliar/*`  avaliação da cliente por token (`feedback_bp`)
 *   - `/static/*`   CSS/JS que essas páginas Jinja referenciam (os bundles Vite usam
 *                   `/assets`, então não há colisão)
 * Nenhum desses prefixos existe como rota nos três React Routers (`/formularios` do ERP é
 * outra rota — o público é só `/f/*`).
 *
 * `/cadastro/*` SAIU desta lista: o formulário Jinja foi aposentado e o endereço agora é servido
 * pelo bundle da vitrine (ver CADASTRO_PREFIX). O que continua no Flask é só `/api/cadastro/*`.
 *
 * `/f/*` NÃO vai para o Flask: é o endereço canônico dos formulários públicos — impresso em
 * bio/integrações — e o formulário atual é o REACT da vitrine (`/catalogo/f/*`). Ver
 * PUBLIC_FORM_PREFIX abaixo: redirect 302 preservando caminho e query, para o link antigo
 * continuar sendo o único divulgado e sempre abrir o formulário novo (o Jinja de
 * `formularios_bp` fica aposentado como superfície).
 */
const BACKEND_PREFIXES = [
  "/api",
  "/uploads",
  "/catalogo/midia",
  // Miniatura da prévia de link (`app/catalogo/routes.py:og_image`). Mesmo motivo do `/midia`:
  // precisa vir ANTES do mount `/catalogo`, senão a SPA pública engole a imagem.
  "/catalogo/og",
  "/portal/photo",
  "/google",
  "/avaliar",
  "/static",
];

/** Endereço canônico curto dos formulários públicos → SPA pública sob /catalogo. */
const PUBLIC_FORM_PREFIX = "/f";

/**
 * Cadastro público de talento: URL curta na raiz do domínio, servida pelo bundle da vitrine.
 *
 * É o endereço divulgado para as artistas (`app.mantoproducoes.com.br/cadastro` e, pelo host
 * dedicado, `portal.mantoproducoes.com.br/cadastro`) e já estava em circulação apontando para o
 * formulário Jinja, agora aposentado. `/catalogo/cadastro` não serve como endereço público:
 * `/catalogo` é a vitrine de personagens, não o lugar onde alguém se candidata.
 *
 * Redirect não resolveria — a barra de endereço passaria a mostrar `/catalogo/cadastro`, que é
 * justamente o que se quer evitar. Então serve o bundle SEM reescrever `req.url`: o
 * `serve-handler` não acha `/cadastro` no `dist` e cai no fallback de SPA, e o roteador do bundle
 * detecta a URL para rodar sem o `basename` de `/catalogo` (`apps/public/src/App.tsx`).
 *
 * O HTML continua referenciando os assets em `/catalogo/assets/*` (o `base` do Vite), servidos
 * pelo mount de `/catalogo` — por isso esse mount precisa seguir alcançável nos dois hosts.
 */
const CADASTRO_PREFIX = "/cadastro";

/** Rotas Jinja remanescentes, casadas por regex para não sombrear rotas do React Router. */
const BACKEND_PATTERNS = [
  /^\/figurinos\/\d+\/print(?:[/?]|$)/,
  // Impressão de todas as fichas de um evento (1 folha por personagem).
  /^\/figurinos\/print-event\/\d+(?:[/?]|$)/,
];

/* ── Prévia de link (Open Graph) das páginas do catálogo ─────────────────────────────────────
 *
 * O link que a equipe manda no WhatsApp é `/catalogo/<slug>` (produto) ou
 * `/catalogo/categoria/<slug>` (tema) — rotas da SPA pública. O WhatsApp (como todo crawler de
 * prévia) NÃO executa JavaScript: ele lê o HTML cru e para por aí. Servido do jeito padrão,
 * esse HTML é o `index.html` do bundle, igual para todas as páginas e sem nenhuma meta tag de
 * Open Graph — resultado: link cinza, sem miniatura e com o título genérico "Manto Produções".
 * Era a rota Jinja `/catalogo/<slug>` que gerava a prévia antes; ela continua existindo no
 * Flask, mas deixou de ser alcançável quando este servidor passou a montar a SPA pública nesse
 * mesmo endereço (feature 186, US6).
 *
 * Então a prévia volta a nascer no servidor: para uma navegação de página de produto ou de tema,
 * buscamos os dados na API do Flask e injetamos `<title>` + Open Graph no `<head>` do
 * `index.html` antes de responder. O bundle segue idêntico — a SPA assume normalmente no
 * navegador de gente de verdade, e o crawler já tem tudo que precisa no HTML inicial.
 *
 * Os dois tipos de página compartilham TODO o fluxo (cache, escape, injeção); a única coisa que
 * varia é qual endpoint responde e como ler o payload — isso mora em `OG_SOURCES`.
 *
 * A `og:image` aponta para `/catalogo/og/...` (miniatura reencodada, ver
 * `app/catalogo/og_ops.py`), nunca para a foto original: arquivo grande faz o WhatsApp entregar
 * o link sem imagem nenhuma.
 */

/** TTL do cache de metadados em memória — catálogo muda pouco; evita 1 request ao Flask por acesso. */
const OG_CACHE_TTL_MS = 5 * 60 * 1000;

/** Teto de entradas do cache, só para o mapa não crescer sem limite em pico de acesso. */
const OG_CACHE_MAX = 500;

/**
 * Timeout da chamada de metadados. Mais folgado que uma leitura JSON simples porque `?og=1` faz
 * o Flask resolver a miniatura (download + reencode) na primeira vez — o custo é pago aqui, uma
 * vez, em vez de ficar pendurado na requisição que o crawler faz à imagem.
 */
const OG_FETCH_TIMEOUT_MS = 8000;

/**
 * Primeiros segmentos de `/catalogo/*` que NÃO são slug de item — são outras telas da SPA.
 * Espelha `apps/public/src/App.tsx`; um nome a mais aqui só custa uma prévia genérica, um a
 * menos custa uma ida inútil à API (que responde 404 e cai no mesmo fallback).
 */
const OG_RESERVED_SEGMENTS = new Set([
  "categorias",
  "categoria",
  "lista-desejos",
  "cadastro",
  "f",
  "avaliar",
  "v",
  "midia",
  "og",
  "assets",
  "index.html",
  "favicon.ico",
]);

/** `"<tipo>:<slug>"` → `{ expires, meta }`. `meta === null` memoriza o 404 e evita martelar o Flask. */
const ogCache = new Map();

/** `index.html` do bundle público, lido uma vez por processo (deploy reinicia o processo). */
let publicIndexHtml = null;

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Descrição do item em texto puro e truncada — `short_description_html` vem do WordPress. */
function plainDescription(html, maxLength = 200) {
  const text = String(html ?? "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&amp;/gi, "&")
    .replace(/\s+/g, " ")
    .trim();
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

/**
 * Página do catálogo que merece prévia: `{ kind, slug }`, ou `null` para qualquer outra URL.
 *
 * `kind` é a chave de `OG_SOURCES` — quem adiciona um tipo de página novo mexe só nos dois.
 */
/**
 * User-agents de robô de prévia de link — os que leem `og:*` e desenham o cartãozinho.
 *
 * `facebookexternalhit` cobre o WhatsApp em boa parte dos casos (a prévia do WhatsApp nasce na
 * infraestrutura da Meta), mas o app também busca com o próprio `WhatsApp/...`, então os dois
 * estão na lista. Um robô fora da lista só perde a miniatura — nunca quebra a página.
 */
const PREVIEW_CRAWLER_UA =
  /facebookexternalhit|whatsapp|twitterbot|slackbot|telegrambot|linkedinbot|discordbot|pinterest|skypeuripreview|googlebot|bingbot|embedly|redditbot|vkshare|applebot/i;

/** `true` quando a requisição veio de um robô de prévia de link. */
function isPreviewCrawler(userAgent) {
  return PREVIEW_CRAWLER_UA.test(String(userAgent ?? ""));
}

function catalogOgTarget(url) {
  const [pathname] = url.split("?");
  if (!pathname.startsWith("/catalogo/")) return null;
  const segments = pathname.slice("/catalogo/".length).split("/").filter(Boolean);

  // O ponto no nome denuncia arquivo do bundle (`index.html`, `favicon.ico`), não slug.
  const isSlug = (value) => Boolean(value) && !value.includes(".");

  if (segments.length === 1) {
    const slug = decodeURIComponent(segments[0]);
    if (!isSlug(slug) || OG_RESERVED_SEGMENTS.has(slug)) return null;
    return { kind: "item", slug };
  }
  // Página de TEMA (a seção do catálogo, `CategoryDetailPage`): dois segmentos, o 1º fixo.
  if (segments.length === 2 && segments[0] === "categoria") {
    const slug = decodeURIComponent(segments[1]);
    return isSlug(slug) ? { kind: "categoria", slug } : null;
  }
  return null;
}

/**
 * O que muda de um tipo de página para o outro: endpoint da API, endereço público, endereço da
 * miniatura e como extrair título/descrição/imagem do payload. Tudo o mais (cache, escape,
 * injeção no `<head>`, fallback para a SPA) é comum aos dois.
 */
const OG_SOURCES = {
  item: {
    apiPath: (slug) => `/api/catalogo/${encodeURIComponent(slug)}`,
    pagePath: (slug) => `/catalogo/${encodeURIComponent(slug)}`,
    imagePath: (slug) => `/catalogo/og/${encodeURIComponent(slug)}.jpg`,
    toMeta: (payload) => ({
      title: payload.name,
      description:
        plainDescription(payload.description_html) ||
        `${payload.name} — personagem do catálogo da Manto Produções.`,
      hasImage: Array.isArray(payload.images) && payload.images.length > 0,
      imageSize: payload.og_image ?? null,
    }),
  },
  categoria: {
    apiPath: (slug) => `/api/catalogo/categoria/${encodeURIComponent(slug)}`,
    pagePath: (slug) => `/catalogo/categoria/${encodeURIComponent(slug)}`,
    imagePath: (slug) => `/catalogo/og/categoria/${encodeURIComponent(slug)}.jpg`,
    toMeta: (payload) => {
      const items = Array.isArray(payload.items) ? payload.items : [];
      const name = payload.category?.name ?? "";
      return {
        title: name,
        // Espelha o subtítulo da própria página ("N personagens nesta seção"), para a prévia
        // dizer a mesma coisa que a pessoa vê ao abrir o link.
        description: `${items.length} ${items.length === 1 ? "personagem" : "personagens"} no tema ${name} — catálogo da Manto Produções.`,
        // A capa do tema é a do primeiro item, mesma regra do card da grade de categorias.
        hasImage: Boolean(items[0]?.cover_image_url),
        imageSize: payload.og_image ?? null,
      };
    },
  },
};

/** Origem pública desta requisição — a `og:image`/`og:url` precisam ser absolutas. */
function requestOrigin(req) {
  const host = (req.headers["x-forwarded-host"] ?? req.headers.host ?? "").split(",")[0].trim();
  const forwardedProto = (req.headers["x-forwarded-proto"] ?? "").split(",")[0].trim();
  const isLocal = /^(localhost|127\.0\.0\.1)(:|$)/.test(host);
  const proto = forwardedProto || (isLocal ? "http" : "https");
  return `${proto}://${host}`;
}

/** Metadados da página pela API do Flask, com cache curto. `null` = inexistente/inativa. */
async function fetchOgMeta(target) {
  const key = `${target.kind}:${target.slug}`;
  const cached = ogCache.get(key);
  if (cached && cached.expires > Date.now()) return cached.meta;

  const source = OG_SOURCES[target.kind];
  let meta = null;
  if (BACKEND_URL) {
    // `?og=1` pede ao Flask as dimensões reais da miniatura (e, de quebra, aquece o cache dela).
    const response = await fetch(`${BACKEND_URL}${source.apiPath(target.slug)}?og=1`, {
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(OG_FETCH_TIMEOUT_MS),
    });
    if (response.ok) {
      meta = source.toMeta(await response.json());
    } else if (response.status !== 404) {
      // 5xx é indisponibilidade momentânea: não vale cachear como "não existe".
      throw new Error(`API respondeu ${response.status}`);
    }
  }

  if (ogCache.size >= OG_CACHE_MAX) ogCache.clear();
  ogCache.set(key, { expires: Date.now() + OG_CACHE_TTL_MS, meta });
  return meta;
}

/** Bloco `og:image` + `twitter` — só as dimensões variam entre ter e não ter cache da miniatura. */
function imageTags(imageUrl, imageSize, alt) {
  if (!imageUrl) return [`<meta name="twitter:card" content="summary" />`];
  return [
    `<meta property="og:image" content="${escapeHtml(imageUrl)}" />`,
    `<meta property="og:image:secure_url" content="${escapeHtml(imageUrl)}" />`,
    `<meta property="og:image:type" content="image/jpeg" />`,
    // Sem width/height o crawler baixa e decodifica a imagem inteira antes de decidir entre card
    // grande e miniatura quadrada — e às vezes desiste antes, entregando o link sem imagem.
    ...(imageSize
      ? [
          `<meta property="og:image:width" content="${escapeHtml(imageSize.width)}" />`,
          `<meta property="og:image:height" content="${escapeHtml(imageSize.height)}" />`,
        ]
      : []),
    `<meta property="og:image:alt" content="${escapeHtml(alt)}" />`,
    `<meta name="twitter:card" content="summary_large_image" />`,
    `<meta name="twitter:image" content="${escapeHtml(imageUrl)}" />`,
  ];
}

/** `index.html` do bundle público com `<title>` e Open Graph da página injetados no `<head>`. */
function renderOgHtml(template, target, meta, origin) {
  const source = OG_SOURCES[target.kind];
  const pageUrl = `${origin}${source.pagePath(target.slug)}`;
  const imageUrl = meta.hasImage ? `${origin}${source.imagePath(target.slug)}` : null;

  const tags = [
    `<title>${escapeHtml(`${meta.title} — Manto Produções`)}</title>`,
    `<meta name="description" content="${escapeHtml(meta.description)}" />`,
    // O template traz `noindex, nofollow`, e crawler de prévia do stack do Facebook (que é o do
    // WhatsApp) pode recusar montar o card com `nofollow`. Segue fora do índice, mas com a
    // prévia grande liberada. A tag original é removida abaixo para não ficarem duas.
    `<meta name="robots" content="noindex, follow, max-image-preview:large" />`,
    `<meta property="og:type" content="website" />`,
    `<meta property="og:site_name" content="Manto Produções" />`,
    `<meta property="og:locale" content="pt_BR" />`,
    `<meta property="og:title" content="${escapeHtml(meta.title)}" />`,
    `<meta property="og:description" content="${escapeHtml(meta.description)}" />`,
    `<meta property="og:url" content="${escapeHtml(pageUrl)}" />`,
    ...imageTags(imageUrl, meta.imageSize, meta.title),
    `<meta name="twitter:title" content="${escapeHtml(meta.title)}" />`,
    `<meta name="twitter:description" content="${escapeHtml(meta.description)}" />`,
  ].join("\n    ");

  // `String.replace` com literal não avisa quando não casa: sem esta checagem, um build que
  // mude o `<head>` faria a prévia voltar a ser genérica em silêncio, sem log nenhum.
  if (!template.includes("</head>")) {
    throw new Error("index.html do bundle público sem </head> — prévia não injetada");
  }
  // O `<title>` do template sai fora para não ficarem dois — alguns crawlers leem o primeiro.
  return template
    .replace(/<title>.*?<\/title>\s*/is, "")
    .replace(/<meta\s+name=["']robots["'][^>]*>\s*/i, "")
    .replace("</head>", `  ${tags}\n  </head>`);
}

/**
 * Responde a página com a prévia embutida. Qualquer falha (Flask fora do ar, timeout, slug
 * inexistente) cai no fluxo normal de SPA: pior prévia, nunca página quebrada.
 */
async function serveOgHtml(req, res, target, fallback) {
  try {
    const [meta, template] = await Promise.all([
      fetchOgMeta(target),
      publicIndexHtml ??
        fs.readFile(path.join(PUBLIC_DIST, "index.html"), "utf8").then((html) => {
          publicIndexHtml = html;
          return html;
        }),
    ]);
    if (!meta) return fallback();

    const body = Buffer.from(renderOgHtml(template, target, meta, requestOrigin(req)), "utf8");
    res.statusCode = 200;
    res.setHeader("content-type", "text/html; charset=utf-8");
    res.setHeader("cache-control", "no-cache");
    res.setHeader("content-length", body.byteLength);
    res.end(body);
  } catch (err) {
    console.error(`[og] ${req.url}: ${err.message}`);
    fallback();
  }
}

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

  // Cadastro público de talento na URL curta (ver CADASTRO_PREFIX). Precisa vir ANTES do bloco
  // de host do portal: sem isto, `portal.mantoproducoes.com.br/cadastro` seria empurrado para
  // `/portal/cadastro`, que não existe no bundle do Portal do Artista.
  if (req.url && matchesPrefix(req.url, CADASTRO_PREFIX)) {
    return handler(req, res, { public: PUBLIC_DIST, ...SERVE_OPTIONS });
  }

  // Formulários públicos: o link curto `/f/<slug>` é o canônico (impresso em bio e
  // conectado em outros softwares) e abre o formulário React da vitrine. Redirect, não
  // reescrita: o bundle público usa `base`/`basename` = `/catalogo` e precisa ver o
  // prefixo na URL do browser. Query preservada (UTMs e afins).
  if (req.url && matchesPrefix(req.url, PUBLIC_FORM_PREFIX)) {
    res.statusCode = 302;
    res.setHeader("location", `/catalogo${req.url}`);
    res.end();
    return;
  }

  // Host dedicado ao portal: leva o caminho para dentro de `/portal` antes dos mounts.
  //
  // Precisa ser REDIRECT, não reescrita interna: o React Router do portal roda com
  // `basename="/portal/"` e lê a URL do browser. Reescrevendo só `req.url`, o bundle certo seria
  // servido mas o roteador não casaria nenhuma rota — tela em branco.
  //
  // E preserva o caminho: o link de redefinição de senha que sai por e-mail é
  // `<PORTAL_URL>/reset-password/<token>`; mandar tudo para `/portal/` descartaria o token.
  //
  // `/catalogo` é exceção junto com `/portal`: a página de cadastro servida acima carrega os
  // assets dela de `/catalogo/assets/*` (o `base` do bundle da vitrine). Sem a exceção, cada
  // asset viraria um 302 para `/portal/catalogo/assets/...` e a página abriria sem JavaScript.
  if (req.url && PORTAL_HOSTS.has((req.headers.host ?? "").split(":")[0].toLowerCase())) {
    if (!matchesPrefix(req.url, "/portal") && !matchesPrefix(req.url, "/catalogo")) {
      res.statusCode = 302;
      res.setHeader("location", `/portal${req.url === "/" ? "/" : req.url}`);
      res.end();
      return;
    }
  }

  // Host da Loja de Interações Virtuais: `alo.mantoproducoes.com.br/<slug>` vira
  // `/catalogo/v/<slug>`, `/pedido/<token>` vira `/catalogo/v/pedido/<token>`, e a **raiz vai
  // para a home da loja** (`/catalogo/v`).
  //
  // A raiz já apontou para `/catalogo/` — o catálogo de eventos —, e isso estava errado: quem
  // entra pelo endereço da loja de conversas recebia a grade de personagens para festa, que é
  // outro produto. Agora cai na vitrine das campanhas publicadas (feature 224e).
  //
  // Redirect pelo mesmo motivo do portal: o bundle público roda com `base`/`basename` =
  // `/catalogo` e lê a URL do browser — reescrever só `req.url` serviria o bundle certo com o
  // roteador sem casar rota nenhuma.
  if (req.url && ALO_HOSTS.has((req.headers.host ?? "").split(":")[0].toLowerCase())) {
    if (!matchesPrefix(req.url, "/catalogo")) {
      const alvo = req.url === "/" ? "/catalogo/v" : `/catalogo/v${req.url}`;
      res.statusCode = 302;
      res.setHeader("location", alvo);
      res.end();
      return;
    }
  }

  // Página de produto ou de tema da vitrine: HTML com Open Graph, para o link compartilhado no
  // WhatsApp abrir com miniatura e nome. Só navegação (GET/HEAD) — o resto segue o fluxo normal.
  //
  // A injeção só vale para CRAWLER. Gente de verdade não ganha nada com meta tag (a SPA monta a
  // página no browser) e pagaria caro por ela: em cache frio a resposta fica pendurada esperando
  // o Flask responder, e o catálogo é a porta de entrada do cliente. Quem não é crawler recebe o
  // bundle na hora, como sempre recebeu.
  const ogTarget =
    (req.method === "GET" || req.method === "HEAD") && isPreviewCrawler(req.headers["user-agent"])
      ? catalogOgTarget(req.url)
      : null;
  if (ogTarget) {
    const serveSpa = () => {
      req.url = req.url.slice("/catalogo".length) || "/";
      handler(req, res, { public: PUBLIC_DIST, ...SERVE_OPTIONS });
    };
    serveOgHtml(req, res, ogTarget, serveSpa);
    return;
  }

  // Fallback existente para os bundles SPA (público, portal, interno).
  for (const { prefix, dir } of MOUNTED_APPS) {
    if (req.url && matchesPrefix(req.url, prefix)) {
      req.url = req.url.slice(prefix.length) || "/";
      return handler(req, res, { public: dir, ...SERVE_OPTIONS });
    }
  }
  return handler(req, res, { public: INTERNAL_DIR, ...SERVE_OPTIONS });
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
