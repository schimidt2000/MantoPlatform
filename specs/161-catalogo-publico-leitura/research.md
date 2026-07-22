# Research: Catálogo Público em React (Leitura)

## §1 — Estado atual de `frontend/apps/public`

**Decisão**: configurar o app do zero seguindo exatamente o padrão já validado em
`apps/internal` (144/145): `react-router-dom` (roteador), `@tanstack/react-query` (dados),
`framer-motion` (animação), `@manto/api-client` e `@manto/ui` (pacotes compartilhados),
Tailwind + PostCSS + Autoprefixer.

**Razão**: hoje `apps/public/package.json` só tem `react`/`react-dom` — é literalmente um
placeholder (`main.tsx` renderiza "Em construção"). Reaproveitar a mesma stack/config de
`apps/internal` (só trocando o tema Tailwind) evita decisão nova de arquitetura e mantém
consistência do monorepo (Princípio I).

**Alternativas consideradas**: nenhuma — a stack já está definida na constituição (v2.0.0,
"Stack e Restrições Técnicas"), não há espaço de decisão aqui.

## §2 — Proxy do Vite em dev

**Decisão**: `apps/public/vite.config.ts` já tem `server.proxy["/api"] → http://localhost:5000`
configurado desde a Fundação (144) — reaproveitado sem alteração.

## §3 — Recriar a galeria animada (feature 143) com Framer Motion

**Decisão**: `ProductGallery.tsx` usa `AnimatePresence`/`motion.img` para o cross-fade entre
fotos e anima a altura do wrapper (`motion.div` com `animate={{ height }}`) calculada a partir
de `naturalWidth`/`naturalHeight` da foto carregada — mesmo cálculo de `computeHeight()` do
`detail.html` atual (largura do wrapper × proporção da foto, limitado a 70vh). Swipe usa os
handlers de pan do próprio Framer Motion (`drag="x"`, `dragConstraints`, `onDragEnd` com
`offset.x`/`velocity.x` para decidir se troca de foto), substituindo os listeners manuais de
Pointer Events do JS vanilla — mesmo comportamento (arrasta ao vivo, solta com distância
suficiente troca, senão volta), API mais idiomática em React. `useReducedMotion()` do Framer
Motion desliga a transição (cross-fade some, troca é instantânea) — mesma regra do CSS
`@media (prefers-reduced-motion: reduce)` de hoje.

**Alternativas consideradas**: manter os listeners de Pointer Events manuais dentro de um
`useEffect` (mais próximo do código atual, mas foge do padrão idiomático de Framer Motion já
usado no resto do app React e duplica o que o `drag` do Framer já resolve).

## §4 — Open Graph / prévia de link (WhatsApp) numa SPA

**Decisão**: nesta fatia, a rota Jinja `/catalogo/<slug>` (com as tags `og:*`/`twitter:*`
server-renderizadas) **continua no ar e é a rota efetivamente compartilhada/linkada
externamente** — o React em `/catalogo/:slug` (app `public`, outro (sub)domínio/porta) é a
experiência de navegação para quem já está dentro do catálogo (clicando de card em card), não
o destino de link externo. Documentado como Assumption na spec (SC-004 cobre que a prévia
continua funcionando).

**Razão**: um SPA React renderiza o `<head>` no navegador via JS; crawlers de prévia de link
(WhatsApp, Facebook, etc.) não executam JS ao buscar a URL — pegariam um `<head>` vazio. Uma
solução de pré-renderização/SSR para isso é claramente maior que esta fatia (a spec 144 já
identifica isso como uma decisão em aberto, não resolvida por nenhuma fatia até agora) e não é
necessária para entregar o valor desta fatia (visitante navegando o catálogo end-to-end em
React). Cortar a rota Jinja agora quebraria toda prévia de link já compartilhada.

**Alternativas consideradas**: (a) pré-renderização estática do detalhe no build (ex.: gerar
HTML por item) — complexidade desproporcional para 5 telas de leitura, decisão melhor tomada
quando a US5 estiver perto do fim e o corte real acontecer; (b) SSR do app `public` — mudaria a
arquitetura (hoje 100% SPA/Vite estático) para todo o monorepo, fora de escopo de uma fatia.

## §5 — Lista de desejos: reescrever em TS mantendo compatibilidade

**Decisão**: `lib/wishlist.ts` porta `catalogo-wishlist.js` função a função (`getAll`, `has`,
`add`, `remove`, `toggle`, `count`, `buildMessage`, `whatsappUrl`), mesma chave de
`localStorage` (`manto_catalogo_wishlist`) e mesmo formato de item (`{slug, name, cover}`).

**Razão**: `localStorage` é por origem (domínio+porta) — o app `public` roda em outro
domínio/porta que a versão Jinja atual, então tecnicamente não há lista "herdada" cruzando as
duas versões hoje (nem havia entre `app.*` e `beta.*` desde a Fundação, 144). Ainda assim,
manter a mesma chave/formato evita qualquer surpresa se as duas versões coexistirem sob o mesmo
domínio em algum ponto da migração, e mantém o princípio de fonte única de comportamento.

## §6 — Onde os endpoints entram no monorepo de API

**Decisão**: `app/api/catalogo_read.py`, registrado em `app/api/__init__.py` (mesmo padrão de
`agenda_read.py`/`talents_read.py`/`figurino_read.py`/`financeiro_read.py`). Nenhum decorator de
RBAC — todos os 4 endpoints são públicos, igual ao blueprint `catalogo_bp` hoje (`@login_required`
nunca aparece em `app/catalogo/routes.py`).

**Razão**: consistência com a convenção `_read.py`/`_write.py` já estabelecida nas fatias
anteriores da migração.
