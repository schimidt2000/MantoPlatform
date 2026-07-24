# Tasks: Gerenciador de Catálogo — UX e Fluxo Ficha↔Catálogo↔Venda

**Input**: Design documents from `specs/186-gerenciador-catalogo-ux/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/api-catalogo-ux.md, quickstart.md

**Organização**: por User Story. MVP = Phase 2 (Foundational) + Phase 3 (US1) + Phase 4 (US2) +
Phase 5 (US3) — as 3 stories P1.

## Phase 1: Setup

- [x] T001 Adicionar `serve-handler` como dependency de `frontend/package.json`

## Phase 2: Foundational (bloqueia US1-US5, não bloqueia US6)

- [x] T002 [P] Estender `api_catalogo_elenco_busca` em `app/api/catalogo_read.py`: incluir
      `photo_url` por Personagem e ampliar `_has_role` para aceitar `RoleName.FIGURINO` além de
      `COMERCIAL`/`SUPERADMIN` — contracts/api-catalogo-ux.md
- [x] T003 [P] Estender `api_admin_catalogo_list`/`_item_summary` em
      `app/api/admin_catalogo_read.py`: incluir `characters: [...]` resumido por item (id, name,
      photo_url, figurino_sheet_id, is_active) — contracts/api-catalogo-ux.md
- [x] T004 [P] Criar `move_characters(character_ids, target_item)` em
      `app/admin/catalog_character_ops.py` — valida `target_item` ativo, reatribui
      `catalog_item_id` em lote numa transação, recalcula `position` dos filhos movidos
- [x] T005 Criar endpoint `POST /api/admin/catalogo/personagens/mover-em-massa` em
      `app/api/admin_catalogo_write.py`, gate `require_superadmin`, delega a T004 —
      contracts/api-catalogo-ux.md

**Checkpoint**: dados com foto/vínculo disponíveis em toda leitura relevante; mover em massa
pronto no backend.

## Phase 3: User Story 1 — Busca visual de Personagem no elenco do evento (P1)

**Independent Test**: em `/events/new`, buscar por nome de um Personagem cadastrado e ver a foto
na sugestão; confirmar que Temas não aparecem.

- [x] T006 [P] [US1] Estender tipo `CatalogElencoCharacter` em
      `frontend/apps/internal/src/lib/catalogoElenco.ts` com `photo_url: string | null`
- [x] T007 [US1] Criar `CharacterAutocomplete.tsx` em `frontend/apps/internal/src/components/` —
      input de busca com dropdown mostrando `<img>` (ou placeholder 🎭) + nome por sugestão,
      recebe `temas: CatalogElencoTema[]` já achatado só em Personagens (filtra Temas fora),
      `onSelect(character)` como callback
- [x] T008 [US1] Substituir o `<select>` "Escolher do catálogo" em
      `frontend/apps/internal/src/components/EventFormBlocks/ElencoBlock.tsx` por
      `<CharacterAutocomplete>`, mantendo o mesmo comportamento de prefill (nome +
      `figurino_sheet_id`) já existente da feature 185

**Checkpoint**: US1 completa e testável de forma independente.

## Phase 4: User Story 2 — Vínculo bidirecional Ficha↔Personagem com indicador (P1)

**Independent Test**: numa Ficha sem vínculo, usar o campo novo para associar a um Personagem;
conferir que o Personagem no catálogo passa a mostrar essa ficha.

- [x] T009 [P] [US2] Adicionar hook `useLinkCharacterToFigurino`/reaproveitar
      `useUpdateCharacter`-like em `frontend/apps/internal/src/lib/adminCatalogo.ts` para uso a
      partir de fora do formulário do Tema (só precisa de `characterId` + `figurinoSheetId`)
- [x] T010 [US2] Adicionar seção "Vincular a um Personagem do Catálogo" em
      `frontend/apps/internal/src/pages/FigurinoFormPage.tsx`: usa `CharacterAutocomplete` (T007)
      para escolher um Personagem, mostra o vínculo atual (se algum Personagem já aponta pra essa
      ficha, via `useCatalogElencoBusca`/`elenco-busca` filtrando client-side) com opção de
      desvincular
- [x] T011 [US2] Adicionar indicador "Sem ficha vinculada" nos cards/linhas de Personagem já
      renderizados (painel de Personagens do Tema, `AdminCatalogCharacterPanel.tsx`) quando
      `figurino_sheet_id` é `null`
- [x] T012 [US2] Adicionar indicador "Sem personagem vinculado" na listagem de Fichas de Figurino
      (`FigurinoListPage.tsx`) quando nenhum Personagem aponta pra aquela ficha, com atalho
      `+ Vincular` que abre o mesmo fluxo de T010 sem sair da lista (ex.: `CharacterAutocomplete`
      inline/popover)

**Checkpoint**: US2 completa e testável de forma independente.

## Phase 5: User Story 3 — Alternador Cards/Árvore (P1)

**Independent Test**: alternar pra Árvore, expandir um Tema com Personagens, ver foto/nome/status
de figurino de cada filho recuado.

- [x] T013 [P] [US3] Estender `CatalogListItem` em
      `frontend/apps/internal/src/lib/adminCatalogo.ts` com `characters: CatalogCharacterSummary[]`
      (novo tipo, espelha T003)
- [x] T014 [US3] Extrair o grid atual de `AdminCatalogoListPage.tsx` para
      `CatalogCardGrid.tsx` em `frontend/apps/internal/src/components/` (mesmo visual de hoje,
      preparando para T015/T017 tocarem só este arquivo)
- [x] T015 [US3] Criar `CatalogTreeView.tsx` em `frontend/apps/internal/src/components/` — por
      Tema: foto, nome, contagem de filhos, controle expandir/recolher (Framer Motion,
      `useReducedMotion()`); expandido, lista os Personagens recuados com linha guia, foto, nome,
      badge de status de figurino
- [x] T016 [US3] Adicionar seletor de modo (Cards/Árvore) no topo de
      `AdminCatalogoListPage.tsx`, estado inicializado de/persistido em `localStorage`
      (`manto_admin_catalogo_view`), renderizando `CatalogCardGrid` ou `CatalogTreeView`

**Checkpoint**: US3 completa e testável de forma independente.

## Phase 6: User Story 4 — Kebab menu + seleção múltipla + ações em massa (P2)

**Independent Test**: selecionar 3 itens no modo Cards, inativar todos de uma vez pela barra
flutuante.

- [x] T017 [P] [US4] Criar `KebabMenu.tsx` em `frontend/apps/internal/src/components/` — botão
      `⋮` + painel ancorado (fecha ao clicar fora/Esc, mesmo espírito de `FilterDropdown`),
      recebe uma lista de `{label, onClick, destructive?}`
- [x] T018 [US4] Em `CatalogCardGrid.tsx`: remover os botões "Inativar"/"Excluir" do corpo do
      card, mover para dentro de um `<KebabMenu>` com itens Editar/Realocar/Inativar/Excluir
      (Excluir com `destructive`)
- [x] T019 [US4] Adicionar checkbox de seleção em cada card (`CatalogCardGrid.tsx`) e em cada
      linha de Tema da árvore (`CatalogTreeView.tsx`), estado de seleção elevado para
      `AdminCatalogoListPage.tsx`
- [x] T020 [US4] Criar `CatalogBulkActionBar.tsx` em `frontend/apps/internal/src/components/` —
      barra fixa no rodapé quando `selectedIds.length > 0`: contagem, painel inline "Mover
      para…" (`<select>` de Temas + confirmar, chama T005), "Inativar selecionados" e "Excluir
      selecionados" (ambos com `window.confirm()` antes, chamando os endpoints já existentes em
      sequência)
- [x] T021 [US4] Integrar `<CatalogBulkActionBar>` em `AdminCatalogoListPage.tsx`

**Checkpoint**: US4 completa e testável de forma independente.

## Phase 7: User Story 5 — Capa e reordenação de fotos (P2)

**Independent Test**: numa edição de Tema com 3 fotos, clicar "Definir como capa" numa foto
diferente e confirmar que o selo migra; arrastar uma foto pra reordenar.

- [x] T022 [US5] Em `AdminCatalogoFormPage.tsx`: badge "⭐ Capa" sobre a foto com
      `coverPhotoId`/índice atual; botão "Definir como capa" em cada outra foto chamando as
      mesmas funções já existentes (`setCoverPhotoId`/`setNewPhotoCoverIndex`), substituindo o
      rádio escondido
- [x] T023 [US5] Adicionar `draggable`/`onDragStart`/`onDragOver`/`onDrop` nativos na grade de
      fotos existentes e novas de `AdminCatalogoFormPage.tsx`, computando a nova ordem e
      aplicando pela mesma função já usada pelas setas (`moveExistingPhoto`), sem duplicar lógica

**Checkpoint**: US5 completa e testável de forma independente.

## Phase 8: User Story 6 — Deploy dual-app / link do menu (P2)

**Independent Test**: `npm run build` + `node server.js` localmente; abrir
`http://localhost:3000/catalogo/` e `http://localhost:3000/catalogo/algum-slug` direto na barra
de endereço — ambos carregam.

- [x] T024 [P] [US6] `frontend/apps/public/vite.config.ts`: `base: mode === "production" ?
      "/catalogo/" : "/"` (usar a assinatura de função de `defineConfig` para acessar `mode`)
- [x] T025 [P] [US6] `frontend/apps/public/src/App.tsx`: `<BrowserRouter basename={import.meta.env.PROD
      ? "/catalogo" : undefined}>`
- [x] T026 [US6] Criar `frontend/server.js` — HTTP server com `serve-handler`: requests
      `/catalogo*` servem de `apps/public/dist` (prefixo removido de `req.url` antes de
      delegar, fallback `/index.html` desse dist); todo o resto serve de `apps/internal/dist`
      (fallback `/index.html` desse dist) — research.md §1
- [x] T027 [US6] Atualizar `frontend/package.json`: script `build` compila os dois apps
      (`npm run build --workspace=apps/internal && npm run build --workspace=apps/public`),
      `start` vira `node server.js`
- [x] T028 [US6] Atualizar `frontend/nixpacks.toml`/`frontend/railway.json` para refletir o novo
      `build`/`start` (comentários atualizados sobre o que cada serviço faz agora)

**Checkpoint**: US6 completa — link "Catálogo" funcional em ambiente equivalente a produção.

## Phase 9: Polish & Verificação Cross-Cutting

- [x] T029 Criar `specs/186-gerenciador-catalogo-ux/verify_186.py` cobrindo: `elenco-busca` inclui
      `photo_url` e aceita papel `FIGURINO`; `GET /admin/catalogo` inclui `characters[]`;
      `mover-em-massa` reatribui `catalog_item_id` de vários Personagens numa chamada e recusa
      `target_item_id`/`character_ids` inválidos; PATCH sem `name` (vínculo a partir da Ficha) e
      `is_active` de Personagem — 18/18 passando
- [x] T030 `ruff check` nos arquivos Python tocados — limpo
- [x] T031 Rodar T029 contra `manto_local` até passar 100%
- [x] T032 [P] Escrever `frontend/apps/internal/e2e/catalogo-ux.spec.ts` (Playwright) cobrindo
      US2/US3/US4: alternar Cards/Árvore, expandir Tema, vincular ficha↔personagem pelos dois
      lados, seleção múltipla + mover em massa no modo Árvore — 4/4 passando
- [x] T033 [P] ~~`vite preview` de build de produção~~ — **decisão de implementação**: `vite
      preview` isolado do app público não reproduz fielmente o setup real (o app espera o prefixo
      `/catalogo` vindo de fora, servido por `frontend/server.js`, não pelo `vite preview` sozinho).
      Verificado por curl/manual em vez de um harness Playwright dedicado: build de produção dos
      dois apps + `node server.js` local, confirmando `/`, `/admin/catalogo`, `/catalogo/`,
      `/catalogo/<slug-inexistente>` (deep link) e o asset JS do app público — todos 200,
      documentado em quickstart.md §3
- [x] T034 Rodar as duas suítes Playwright (+ regressão completa das features 180/185) — 28/28
      (`apps/internal`, 1 skip pré-existente não relacionado) e 3/3 (`apps/public`)
- [x] T035 [P] `npx tsc --noEmit && npm run build` em `frontend/apps/internal` — limpo
- [x] T036 [P] `npx tsc --noEmit && npm run build` em `frontend/apps/public` — limpo, `base`
      `/catalogo/` confirmado no `dist/index.html`
- [x] T037 Build + `node server.js` local — roteiro manual do quickstart.md §4 no navegador
      (Cards, Árvore, quick-vincular, barra de ações em massa) — conferido visualmente
- [x] T038 Atualizar `docs/changelog.html` e republicar no link existente

## Dependencies & Execution Order

- **Phase 1-2** → bloqueiam US1-US5 (dados de foto/característica e endpoint de mover)
- **US1, US2, US3** → independentes entre si após Phase 2
- **US4** → depende de US3 (kebab/seleção vivem dentro de `CatalogCardGrid`/`CatalogTreeView`
  criados na US3)
- **US5** → independente, só depende do formulário de Tema já existente
- **US6** → totalmente independente de US1-US5 (infraestrutura de deploy) — pode ser feita em
  paralelo a qualquer momento
- **Phase 9** → depende de tudo que está sendo testado/documentado

## Implementation Strategy

**MVP**: Phase 1+2 + US1 + US2 + US3 (P1). US4/US5/US6 (P2) somam valor incremental.
