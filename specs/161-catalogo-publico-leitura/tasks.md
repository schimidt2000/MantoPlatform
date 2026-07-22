# Tasks: Catálogo Público em React (161)

**Input**: Design documents from `specs/161-catalogo-publico-leitura/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/catalogo-leitura-endpoints.md, quickstart.md

**Tests**: verificação é o script de paridade
`scripts/db/verify_161_catalogo_publico_leitura.py` contra `manto_local`, gerado na Phase de
Polish.

**Organização**: 2 user stories (US1 navegar/ver detalhe, US2 lista de desejos), nessa ordem de
prioridade.

## Phase 1: Setup

- [ ] T001 Adicionar ao `frontend/apps/public/package.json` as dependências já usadas em
      `apps/internal`: `react-router-dom`, `@tanstack/react-query`, `framer-motion`,
      `@manto/api-client`, `@manto/ui` (dependencies); `autoprefixer`, `postcss`, `tailwindcss`
      (devDependencies); trocar o script `build` para `tsc --noEmit && vite build` (mesmo padrão
      de `apps/internal`) e adicionar `typecheck`.
- [ ] T002 [P] Criar `frontend/apps/public/postcss.config.js` (idêntico ao de `apps/internal`).
- [ ] T003 [P] Criar `frontend/apps/public/tailwind.config.ts`: tokens portados de
      `app/templates/catalogo/_head_shared.html` (`--cat-*`) para o mesmo formato de tema usado
      por `apps/internal/tailwind.config.ts` — `bg` (`#faf6ef`), `panel` (`#fff`), `ink`
      (`#241c2e`), `muted` (`#7d7188`), `line` (`#e7ddcd`), `accent.DEFAULT` (`#4a2f6b`),
      `accent.dark` (`#2f1d47`), `accent.soft` (`rgba(74,47,107,.08)`), `ring` (`rgba(74,47,107,.30)`),
      `gold` (`#b1793a`) + `gold-soft` (`rgba(177,121,58,.12)`); `borderRadius.lg` = `18px`
      (`--cat-radius`); `fontFamily.display` (Fraunces) e `fontFamily.sans` (Manrope) — assim os
      componentes `@manto/ui` (que usam classes `bg-accent`/`bg-panel`/etc.) herdam
      automaticamente a identidade visual do catálogo sem duplicar estilo (Princípio I).
- [ ] T004 [P] Criar `frontend/apps/public/src/index.css`: diretivas `@tailwind`
      base/components/utilities + `@import` das fontes Google (Fraunces + Manrope, mesma URL de
      `_head_shared.html`) + `html { scroll-behavior: smooth }` com guarda
      `@media (prefers-reduced-motion: reduce)`.
- [ ] T005 Reescrever `frontend/apps/public/src/main.tsx`: remover o placeholder "Em
      construção", envolver `<App />` em `QueryClientProvider` com `createQueryClient()`
      (`@manto/api-client`, mesmo padrão de `apps/internal/src/main.tsx`), importar `./index.css`.
- [ ] T006 Criar `frontend/apps/public/src/App.tsx` com `BrowserRouter`/`Routes` — rotas `/`,
      `/categorias`, `/categoria/:slug`, `/:slug`, `/lista-desejos` — apontando por enquanto
      para componentes placeholder (substituídos nas fases seguintes).
- [ ] T007 Adicionar ao `frontend/package.json` raiz os scripts `dev:public`, `build:public`,
      `typecheck:public` (mesmo padrão de `dev:internal`/`build:internal`/`typecheck:internal`,
      trocando `--workspace=apps/internal` por `--workspace=apps/public`).

## Phase 2: Foundational

- [ ] T008 Criar `app/api/catalogo_read.py` (NOVO): 4 endpoints públicos (sem
      `@login_required`) —
      - `GET /catalogo` → reaproveita a query de `catalogo_bp.index` (`app/catalogo/routes.py`):
        itens ativos ordenados por nome, contagem de categorias com item, `whatsapp_number` via
        `_whatsapp_target()` (`app/formularios/routes.py`). Shape conforme
        `contracts/catalogo-leitura-endpoints.md`.
      - `GET /catalogo/categorias` → reaproveita `catalogo_bp.categorias`.
      - `GET /catalogo/categoria/<slug>` → reaproveita `catalogo_bp.categoria_detail`; 404 se
        categoria não existe ou sem item ativo.
      - `GET /catalogo/<slug>` → reaproveita `catalogo_bp.detail` (sem os campos de Open Graph);
        inclui `related` (até 6, mesma categoria); 404 se slug não existe ou item inativo.
      Type hints e docstring (Google style) em cada função; registrado no blueprint `api_bp`.
- [ ] T009 Importar `catalogo_read` em `app/api/__init__.py` (mesmo padrão dos demais módulos
      `_read`).
- [ ] T010 [P] Criar `frontend/apps/public/src/lib/catalogo.ts`: tipos TS (`CatalogItemSummary`,
      `CatalogItemDetail`, `CatalogCategorySummary`, conforme `data-model.md`) + hooks
      `useCatalogList()`, `useCategories()`, `useCategoryDetail(slug)`, `useProductDetail(slug)`
      usando `useQuery` (`@tanstack/react-query`) e `apiFetch` (`@manto/api-client`).
- [ ] T011 [P] Criar `frontend/apps/public/src/components/ProductCard.tsx`: card reutilizável
      (capa, nome, até 3 chips de categoria, botão de favoritar sobreposto) — usado pela grade
      geral, grade de categoria e relacionados do detalhe.

## Phase 3: User Story 1 — Navegar o catálogo e ver o detalhe de um produto (P1)

**Goal**: visitante navega a grade geral/por categoria e abre o detalhe de um produto com a
galeria animada.

**Independent Test**: abrir a grade, filtrar por categoria, abrir um produto e ver a galeria
(cross-fade + swipe) e os relacionados — tudo em 320–430px sem quebrar.

- [ ] T012 [US1] Criar `frontend/apps/public/src/pages/CatalogGridPage.tsx`: usa
      `useCatalogList()` (T010); skeleton de grade durante loading; estado vazio amigável;
      barra de busca (filtro client-side por nome/categoria, `normalize` sem acento — porta a
      lógica de `index.html` atual) + tabs de categoria (`cat.name`, com contagem); grid de
      `ProductCard` (T011); estado "nenhum resultado" quando busca/filtro não bate com nada.
- [ ] T013 [P] [US1] Criar `frontend/apps/public/src/pages/CategoriesPage.tsx`: usa
      `useCategories()` (T010); grid de cards de categoria (foto de capa + overlay com nome e
      contagem); estado vazio amigável.
- [ ] T014 [P] [US1] Criar `frontend/apps/public/src/pages/CategoryDetailPage.tsx`: usa
      `useCategoryDetail(slug)` (T010); grid de `ProductCard` (T011); estado "não encontrado"
      (404 do endpoint) renderiza a mesma mensagem amigável de `invalid.html`.
- [ ] T015 [US1] Criar `frontend/apps/public/src/components/ProductGallery.tsx`: galeria
      animada com Framer Motion (`research.md` §3) — `motion.div` anima a altura do wrapper
      (calculada de `naturalWidth/naturalHeight` da foto atual, limitada a 70vh),
      `AnimatePresence`/`motion.img` faz o cross-fade ao trocar, `drag="x"` +
      `onDragEnd(offset, velocity)` implementa o swipe (troca de foto se ultrapassar o limiar de
      distância), miniaturas clicáveis abaixo; `useReducedMotion()` desliga a transição.
- [ ] T016 [US1] Criar `frontend/apps/public/src/pages/ProductDetailPage.tsx`: usa
      `useProductDetail(slug)` (T010); renderiza `ProductGallery` (T015), nome, categorias,
      `description_html` (`dangerouslySetInnerHTML`), botão "copiar link" (feedback "Copiado!"
      por 1.5s), `WishlistButton` (stub até Phase 4), grid de relacionados com `ProductCard`
      (T011); estado "não encontrado" (404) com a mesma mensagem amigável.
- [ ] T017 [US1] Em `App.tsx` (T006), substituir os placeholders de `/`, `/categorias`,
      `/categoria/:slug`, `/:slug` pelas páginas reais (T012/T013/T014/T016).

**Checkpoint**: US1 completa e testável isoladamente — navegação e detalhe funcionam ponta a
ponta (favoritar ainda sem efeito real, Phase 4 conecta).

---

## Phase 4: User Story 2 — Favoritar itens e ver a lista de desejos (P2)

**Goal**: visitante favorita produtos e vê a lista reunida, com envio por WhatsApp.

**Independent Test**: favoritar 2+ produtos, abrir `/lista-desejos`, ver os itens persistidos
(reload da página) e o link de WhatsApp correto.

- [ ] T018 [US2] Criar `frontend/apps/public/src/lib/wishlist.ts`: porta
      `app/static/js/catalogo-wishlist.js` para TS (`research.md` §5) — mesma chave
      `manto_catalogo_wishlist`, mesmo shape `{slug, name, cover}`; funções `getAll`, `has`,
      `add`, `remove`, `toggle`, `count`, `buildMessage`, `whatsappUrl`; degrada sem quebrar se
      `localStorage` estiver indisponível (mesmo `try/catch` do JS original).
- [ ] T019 [P] [US2] Criar `frontend/apps/public/src/components/WishlistButton.tsx`: usa
      `lib/wishlist.ts` (T018) — estado local sincronizado com `localStorage`, texto/estilo
      alternam entre "♡ Adicionar à lista" e "✓ Na lista" ao clicar (Princípio V); conectar este
      componente no lugar do stub em `ProductCard.tsx` (T011) e `ProductDetailPage.tsx` (T016).
- [ ] T020 [P] [US2] Criar `frontend/apps/public/src/components/WishlistFloat.tsx`: botão
      flutuante fixo (canto inferior direito) com contador (`lib/wishlist.ts`), oculto quando
      count=0, link para `/lista-desejos`; montado uma vez em `App.tsx` (fora das `Routes`, para
      aparecer em todas as páginas exceto ela mesma).
- [ ] T021 [US2] Criar `frontend/apps/public/src/pages/WishlistPage.tsx`: lista os itens de
      `lib/wishlist.ts` (imagem, nome, botão remover), estado vazio amigável; botão "Enviar para
      o vendedor" (desabilitado se lista vazia) monta `whatsappUrl` usando o `whatsapp_number` de
      `useCatalogList()` (T010) e abre em nova aba.
- [ ] T022 [US2] Em `App.tsx`, substituir o placeholder de `/lista-desejos` por `WishlistPage`
      (T021) e montar `WishlistFloat` (T020) globalmente.

**Checkpoint**: US2 completa — com ela, as 5 telas do catálogo público estão 100% em React.

---

## Phase 5: Polish & Verificação

- [ ] T023 Criar `scripts/db/verify_161_catalogo_publico_leitura.py` (gitignored): test client
      Flask contra `manto_local`, requests fora de `app_context` — cobre: paridade dos 4
      endpoints com as rotas Jinja equivalentes (mesmos itens/categorias/fotos/relacionados para
      os mesmos dados), 404 de slug/categoria inexistente ou inativo, e que todos os endpoints
      respondem 200 sem nenhuma sessão autenticada (rota pública, sem gate).
- [ ] T024 Rodar `ruff check app/api/catalogo_read.py`.
- [ ] T025 Rodar `npm run typecheck:public` e `npm run build:public`.
- [ ] T026 Conferência mobile (320–430px) das 5 telas — grade, categorias, categoria, detalhe
      (galeria/swipe), lista de desejos — e do botão flutuante (não deve sobrepor conteúdo nem
      ficar atrás do teclado virtual) — Princípio VIII.
- [ ] T027 Atualizar `docs/changelog.html` com entrada em linguagem simples (entrada 161) e
      republicar no artifact já existente (mesmo link).

## Dependencies

Setup (Phase 1) → Foundational (Phase 2) → US1 (Phase 3) → US2 (Phase 4) → Polish (Phase 5).

US2 depende de US1 (favoritar aparece em `ProductCard`/`ProductDetailPage`, criados na Phase 3;
`WishlistFloat` é montado em `App.tsx` já roteado pela Phase 3) — não é paralelizável com US1,
diferente do padrão usual de stories independentes. Dentro de cada phase: tarefas `[P]` tocam
arquivos distintos e podem rodar em paralelo; tarefas sem `[P]` têm alguma dependência sequencial
(mesmo arquivo ou consomem o resultado da tarefa anterior).

## Implementation Strategy

MVP = US1 (navegar + ver detalhe — 95%+ do valor de negócio do catálogo). US2 (lista de desejos)
incrementa sobre a mesma base sem mudar arquitetura. Com esta fatia completa, o Catálogo Público
fica 100% em React — próxima fatia da US5 é `/cadastro` público (fora de escopo aqui, ver
Assumptions em `spec.md`).
