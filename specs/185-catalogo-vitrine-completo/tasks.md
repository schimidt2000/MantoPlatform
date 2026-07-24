# Tasks: Catálogo Vitrine Completo — Temas, Personagens e Vídeo

**Input**: Design documents from `specs/185-catalogo-vitrine-completo/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/api-catalogo.md, quickstart.md

**Tests**: o usuário pediu explicitamente verificação via Playwright contra `manto_local` — tasks
de teste estão incluídas (T044-T047). O padrão de verificação funcional backend do projeto
(script com test client do Flask) também está incluído (T041-T043).

**Organização**: por User Story, para permitir implementação e teste independentes. MVP =
Phase 2 (Foundational) + Phase 3 (US1) + Phase 4 (US2) + Phase 5 (US3) — as 3 stories P1.

## Phase 1: Setup

- [x] T001 ~~Adicionar `@playwright/test` + `frontend/playwright.config.ts`~~ — **descoberto
      durante implementação**: `frontend/apps/internal` já tinha Playwright configurado desde a
      feature 180 (`playwright.config.ts` + `e2e/global-setup.ts` com login via
      `E2E_USER_EMAIL`/`E2E_USER_PASSWORD`); reaproveitado sem mudança. Só faltava em
      `frontend/apps/public` (sem login) — criado `frontend/apps/public/playwright.config.ts` +
      script `e2e` no `package.json`, reaproveitando a mesma versão de `@playwright/test` já
      hoisted no monorepo (sem dependência nova).
- [x] T002 [P] `frontend/apps/public/e2e/` criado com `catalogo-publico.spec.ts`;
      `frontend/apps/internal/e2e/` já existia (feature 180) — specs novos adicionados junto dos
      já existentes, sem `.gitignore`/`tsconfig.json` extra (o app já cobre isso).

## Phase 2: Foundational (bloqueia todas as User Stories)

**Objetivo**: schema de dados novo + núcleo de validação de vídeo + CRUD puro de Personagem —
sem isso, nenhuma User Story tem dado para testar.

- [x] T003 Adicionar `class CatalogCharacter(db.Model)` em `app/models.py` (tabela
      `catalog_characters`: id, catalog_item_id FK CASCADE, name, slug único, photo_url,
      video_url, figurino_sheet_id FK SET NULL, position, is_active, created_at) e
      `video_url = db.Column(...)` em `CatalogItem`, com relacionamento `characters`
      (`cascade="all, delete-orphan"`, `order_by="CatalogCharacter.position"`) — ver
      `data-model.md`
- [x] T004 Criar migration manual em `migrations/versions/` (`down_revision="4e6f8a1c2d5b"`) com
      `upgrade()`/`downgrade()` completos para a tabela `catalog_characters` e a coluna
      `catalog_items.video_url` (data-model.md §Migration Alembic)
- [x] T005 Aplicar a migration em `manto_local` (`python -m flask db upgrade` com
      `DATABASE_URL` da cópia local) e confirmar `python -m flask db heads`
- [x] T006 [P] Criar `app/catalogo/media.py` com `classify_video_url(url: str) -> Literal["mp4",
      "drive", "vimeo"] | None` (regex por provedor, função pura, docstring) — research.md §2
- [x] T007 [P] Criar `app/admin/catalog_character_ops.py` com `CatalogValidationError` reusada
      (importar de `app.admin.catalog_ops`), e funções puras: `unique_character_slug(tema_slug,
      name)`, `create_character(item, *, name, video_url, figurino_sheet_id, photo_file)`,
      `update_character(character, **kwargs)`, `delete_character(character)` — mesmo padrão de
      `catalog_ops.py` (upload via `app/storage.py`, `audit()`, `db.session.commit()`)
- [x] T008 Estender `create_product`/`update_product` em `app/admin/catalog_ops.py` para aceitar e
      validar `video_url` (usa `classify_video_url`, levanta `CatalogValidationError("video_url",
      ...)` se inválido)

**Checkpoint**: schema criado, migration aplicada em `manto_local`, núcleo de validação/CRUD pronto.

## Phase 3: User Story 1 — Cliente descobre Tema e elenco de Personagens (P1) 🎯 MVP

**Goal**: vitrine pública lista Personagens filhos de um Tema, cada um adicionável à lista de
interesse independentemente do Tema completo.

**Independent Test**: publicar um Tema com 2 Personagens (via script de seed ou Phase 5 já
concluída) e abrir `/catalogo/:slug` sem sessão — conferir seção "Elenco Individual" e
adição individual à lista de interesse.

- [x] T009 [P] [US1] Estender `_item_summary`/`api_catalogo_detail` em `app/api/catalogo_read.py`
      para incluir `characters: [...]` (só `is_active=true`, ordenados por `position`) na
      resposta de `GET /api/catalogo/<slug>` — contracts/api-catalogo.md
- [x] T010 [P] [US1] Estender tipos e hook `useProductDetail` em
      `frontend/apps/public/src/lib/catalogo.ts` com a interface `CatalogCharacter`
- [x] T011 [P] [US1] Estender `WishlistItem`/`wishlist.ts`
      (`frontend/apps/public/src/lib/wishlist.ts`) com `kind?: "tema" | "personagem"` e
      `parentSlug?: string`; atualizar `buildMessage()`/`whatsappUrl()` para montar o link
      correto por tipo — research.md §5
- [x] T012 [US1] Estender `WishlistButton.tsx`
      (`frontend/apps/public/src/components/WishlistButton.tsx`) para aceitar `kind`/`parentSlug`
      opcionais e repassá-los ao `wishlist.add()`/`toggle()`
- [x] T013 [US1] Criar `CharacterCard.tsx` em `frontend/apps/public/src/components/` — foto ou
      preview de vídeo, nome, botão "+ Adicionar à lista" (usa `WishlistButton` com
      `kind="personagem"`)
- [x] T014 [US1] Criar `CharacterGrid.tsx` em `frontend/apps/public/src/components/` — seção
      "Personagens deste Tema / Elenco Individual", grid responsivo de `CharacterCard`; não
      renderiza nada se `characters.length === 0` (Edge Case da spec)
- [x] T015 [US1] Integrar `<CharacterGrid>` em `ProductDetailPage.tsx`
      (`frontend/apps/public/src/pages/ProductDetailPage.tsx`), abaixo do bloco "Você também pode
      gostar"
- [x] T016 [US1] Suportar `?personagem=<slug>` em `ProductDetailPage.tsx`: scroll automático até o
      `CharacterCard` correspondente + destaque visual temporário (research.md §4)
- [x] T017 [US1] Adicionar botão "Copiar link" por Personagem em `CharacterCard.tsx`, copiando
      `${origin}/${temaSlug}?personagem=${slug}`

**Checkpoint**: US1 completa e testável de forma independente.

## Phase 4: User Story 2 — Vídeo na galeria pública (P1)

**Goal**: galeria pública reproduz vídeo (autoplay mudo/loop/playsinline + som/fullscreen) com
transição de altura animada entre mídias de proporções diferentes.

**Independent Test**: item com 1 foto horizontal + 1 vídeo vertical cadastrados; navegar a galeria
pública e conferir autoplay mudo, botões de som/tela cheia, transição de altura sem salto.

- [x] T018 [P] [US2] Adicionar `video_url`/`video_kind` (via `classify_video_url`) na resposta de
      `GET /api/catalogo/<slug>` em `app/api/catalogo_read.py` (campo do Tema, além de
      `characters[].video_url`/`video_kind` já incluído em T009)
- [x] T019 [P] [US2] Estender tipos em `frontend/apps/public/src/lib/catalogo.ts` com
      `video_url`/`video_kind` no Tema e no `CatalogCharacter`
- [x] T020 [US2] Criar `VideoPlayer.tsx` em `frontend/apps/public/src/components/` — elemento
      `<video>` nativo para `video_kind` "mp4"/"drive" (autoplay, muted, loop, playsinline, botão
      de mute e botão de fullscreen customizados) e `<iframe>` Vimeo com parâmetros nativos
      (`autoplay=1&muted=1&loop=1&background=1&playsinline=1`) para `video_kind` "vimeo" —
      research.md §1
- [x] T021 [US2] Estender `ProductGallery.tsx`
      (`frontend/apps/public/src/components/ProductGallery.tsx`) para aceitar uma lista de itens
      de mídia mista (fotos existentes + `video_url` opcional do Tema como item adicional),
      calculando a altura animada também a partir de `videoWidth`/`videoHeight`
      (`onLoadedMetadata`) quando o item atual é vídeo — mantém `useReducedMotion()`
- [x] T022 [US2] Aplicar `VideoPlayer` também nos `CharacterCard.tsx` (preview de vídeo do
      Personagem, silencioso, sem autoplay em lista — só no card expandido/detalhe)
- [x] T023 [US2] Tratar `video_url` inválida/indisponível: `onError` do `<video>` remove o item da
      galeria silenciosamente (Edge Case da spec) — log local (console.warn) para depuração, sem
      Toast ao cliente público

**Checkpoint**: US2 completa e testável de forma independente (pode reusar dado de teste do US1).

## Phase 5: User Story 3 — Gerenciador Interno: Temas, Personagens, tags (P1)

**Goal**: staff cadastra Personagens (nome/foto/vídeo/figurino) e usa chip input de tags no
Gerenciador de Catálogo Interno.

**Independent Test**: em `/admin/catalogo`, criar Tema com 2 Personagens (foto+vídeo+figurino
vinculado) e tags via chip input; conferir refletido na vitrine pública (Phase 3/4).

- [x] T024 [P] [US3] Endpoints em `app/api/admin_catalogo_write.py`: `POST
      /api/admin/catalogo/<item_id>/personagens`, `PATCH
      /api/admin/catalogo/personagens/<character_id>`, `DELETE
      /api/admin/catalogo/personagens/<character_id>` — gate `require_superadmin`, delegam a
      `catalog_character_ops` (T007) — contracts/api-catalogo.md
- [x] T025 [P] [US3] Estender `POST/PATCH /api/admin/catalogo` em
      `app/api/admin_catalogo_write.py` para aceitar `video_url` (usa T008)
- [x] T026 [P] [US3] Estender `GET /api/admin/catalogo/<item_id>` em
      `app/api/admin_catalogo_read.py` para incluir `video_url` e `characters[]` (com
      `figurino_sheet_id`, incluindo inativos) — contracts/api-catalogo.md
- [x] T027 [P] [US3] Criar `ChipInput.tsx` em
      `frontend/apps/internal/src/components/` — tag input tokenizado genérico: Enter/vírgula
      cria chip, botão `✕` remove, prop `suggestions: string[]` para autocomplete (filtra por
      texto digitado), `value: string[]`/`onChange` controlado, zero dependência nova (só
      Tailwind + `@manto/ui`)
- [x] T028 [US3] Adicionar hook `useCatalogTagSuggestions()` em
      `frontend/apps/internal/src/lib/adminCatalogo.ts` reaproveitando
      `GET /api/admin/catalogo` (já retorna produtos) ou criando um endpoint leve
      `GET /api/admin/catalogo/tags` que chama `catalog_ops.all_tags()` (já existe,
      `app/admin/catalog_ops.py:55`) — Princípio I, reusar `all_tags()` existente
- [x] T029 [US3] Adicionar rota `GET /api/admin/catalogo/tags` em
      `app/api/admin_catalogo_read.py`, delegando a `catalog_ops.all_tags()`
- [x] T030 [US3] Substituir o input de texto cru de tags por `<ChipInput>` em
      `AdminCatalogoFormPage.tsx`
      (`frontend/apps/internal/src/pages/AdminCatalogoFormPage.tsx`), convertendo de/para a string
      `tags` (join/split por vírgula) esperada por `SaveCatalogItemInput`
- [x] T031 [US3] Adicionar campo `video_url` (input de texto + validação inline de formato) ao
      formulário do Tema em `AdminCatalogoFormPage.tsx`, propagando erro de campo
      (`fieldErrors.video_url`)
- [x] T032 [US3] Adicionar hooks de CRUD de Personagem em
      `frontend/apps/internal/src/lib/adminCatalogo.ts`:
      `useCreateCharacter/useUpdateCharacter/useDeleteCharacter` (multipart, mesmo padrão de
      `useCreateCatalogItem`)
- [x] T033 [US3] Criar `AdminCatalogCharacterPanel.tsx` em
      `frontend/apps/internal/src/components/` — lista de Personagens do Tema em edição: nome,
      upload de foto, campo de URL de vídeo, dropdown de busca de Ficha de Figurino (reusa
      `useFigurinoSheets()` de `frontend/apps/internal/src/lib/figurino.ts`), reordenar (‹ ›,
      mesmo padrão de `moveExistingPhoto`), excluir com `window.confirm()` (Princípio V)
- [x] T034 [US3] Integrar `<AdminCatalogCharacterPanel>` em `AdminCatalogoFormPage.tsx` (só exibido
      quando `isEdit === true` — Personagem depende de `catalog_item_id` já existente)

**Checkpoint**: US3 completa — staff consegue alimentar dados que US1/US2 exibem.

## Phase 6: User Story 4 — Auto-vínculo de figurino em Novo Evento (P2)

**Goal**: ao escolher um Personagem do catálogo no formulário de evento, a Ficha de Figurino é
pré-preenchida automaticamente.

**Independent Test**: criar evento, buscar Personagem com `figurino_sheet_id` vinculada,
confirmar prefill da ficha na linha do elenco.

- [x] T035 [US4] Endpoint `GET /api/catalogo/elenco-busca` em `app/api/catalogo_read.py` — gate
      `COMERCIAL`/`SUPERADMIN` (mesmo padrão `_has_role` de `agenda_write.py`), retorna Temas
      ativos + Personagens ativos achatados (`figurino_sheet_id` incluso) —
      contracts/api-catalogo.md
- [x] T036 [US4] Hook `useCatalogElencoBusca()` em `frontend/apps/internal/src/lib/catalogoElenco.ts`
      (novo arquivo pequeno) consumindo o endpoint T035
- [x] T037 [US4] Adicionar ação "Escolher do catálogo" na `CharacterRow` de
      `frontend/apps/internal/src/components/EventFormBlocks/ElencoBlock.tsx`: abre um seletor
      (Tema → Personagem ou Tema completo) e faz `onChange({ ...value, name: escolhido.name,
      figurino_sheet_id: escolhido.figurino_sheet_id ?? value.figurino_sheet_id })` — prefill
      único, sem persistir vínculo novo (research.md §6, FR-014)

**Checkpoint**: US4 completa e testável de forma independente (depende só de T035-T037 + dado de US3).

## Phase 7: User Story 5 — `noindex` no catálogo público (P3)

**Goal**: `/catalogo` e `/catalogo/:slug` não são indexados por buscadores.

**Independent Test**: inspecionar `<head>` renderizado de ambas as rotas.

- [x] T038 [P] [US5] ~~Criar `useNoIndex()`~~ — **descoberto durante implementação**:
      `frontend/apps/public/index.html` já tem `<meta name="robots" content="noindex, nofollow">`
      estático desde a feature 161 (commit `813c73e`, 2026-07-22), cobrindo 100% das rotas do app
      público. Um hook novo duplicaria a tag (confirmado por e2e — 2 `<meta>` na página). Tarefa
      fechada sem código novo (Princípio I).
- [x] T039 [US5] ~~Chamar `useNoIndex()` em `CatalogGridPage.tsx`~~ — não necessário, ver T038.
- [x] T040 [US5] ~~Chamar `useNoIndex()` em `ProductDetailPage.tsx`~~ — não necessário, ver T038.

**Checkpoint**: US5 completa e testável de forma independente.

## Phase 8: Polish & Verificação Cross-Cutting

- [x] T041 Criar script de verificação com test client do Flask (requests fora de `app_context`,
      contra `manto_local`) cobrindo: criar Tema com Personagens (201), validar `video_url`
      inválida (400 com `fields`), `GET /api/catalogo/<slug>` retorna `characters` ativos,
      exclusão de Tema cascade-apaga Personagens, exclusão de Ficha de Figurino não quebra
      Personagem vinculado (`figurino_sheet_id` vira `NULL`), `GET /api/catalogo/elenco-busca`
      nega acesso sem role `COMERCIAL`/`SUPERADMIN` (403) — caminho real
      `specs/185-catalogo-vitrine-completo/verify_185.py` (convenção do repo é `specs/*/verify_*.py`,
      não `scripts/`), 16/16 passando
- [x] T042 Rodar `ruff check` nos arquivos Python tocados (T003-T009, T018, T024-T026, T029, T035)
- [x] T043 Rodar o script T041 contra `manto_local` e corrigir até passar 100%
- [x] T044 [P] Escrever `frontend/e2e/catalogo-publico.spec.ts` (Playwright) cobrindo US1/US2/US5:
      abrir `/catalogo/:slug` de um Tema seedado, conferir `noindex` no head, grid de Personagens,
      adicionar Tema e Personagem à lista separadamente, vídeo em autoplay mudo
- [x] T045 [P] Escrever `frontend/e2e/catalogo-admin.spec.ts` (Playwright) cobrindo US3: login
      staff, criar Tema com chip input de tags, adicionar Personagem com vínculo de figurino
- [x] T046 [P] Escrever `frontend/e2e/eventos-elenco-catalogo.spec.ts` (Playwright) cobrindo US4:
      Novo Evento, escolher Personagem do catálogo, conferir prefill de figurino
- [x] T047 Rodar `npx playwright test` (os 3 specs acima) contra `manto_local` + `dev:public`/
      `dev:internal` locais, corrigir até passar 100%
- [x] T048 [P] `npx tsc --noEmit && npm run build` em `frontend/apps/public`
- [x] T049 [P] `npx tsc --noEmit && npm run build` em `frontend/apps/internal`
- [x] T050 Verificar viewport mobile (320–430px) de `/catalogo/:slug` (Personagens, vídeo, botões
      de ação) — Princípio VIII
- [x] T051 Atualizar `docs/changelog.html` com a entrega desta feature (linguagem simples,
      pt-BR) e republicar no link existente
- [x] T052 Avaliado: `CatalogCharacter` segue exatamente o padrão de entidade-filha já documentado
      (mesmo shape de `CatalogItemImage` — FK + cascade + `*_ops.py` puro) e `ChipInput` é só um
      componente novo de UI, não uma convenção de arquitetura nova. `.claude/skills/architecture.md`
      não precisou de atualização.

## Dependencies & Execution Order

- **Phase 1 (Setup)** → sem dependências, pode rodar a qualquer momento antes da Phase 8
- **Phase 2 (Foundational)** → bloqueia Phases 3-7 (todas dependem do schema/CRUD de
  `CatalogCharacter`)
- **Phase 3 (US1)**, **Phase 4 (US2)**, **Phase 5 (US3)** → independentes entre si após a Phase 2
  (podem ser implementadas em paralelo por pessoas/sessões diferentes), mas US1/US2 precisam de
  dado criado via US3 (ou seed manual) para teste manual end-to-end
- **Phase 6 (US4)** → depende apenas da Phase 2 (schema) + endpoint próprio (T035-T037);
  não depende de US1/US2/US3 estarem com UI pronta, só do dado existir no banco
- **Phase 7 (US5)** → totalmente independente, só depende das páginas já existirem (não depende
  de nenhuma outra story desta feature)
- **Phase 8 (Polish)** → depende de todas as phases anteriores relevantes ao que está sendo
  testado/documentado

## Parallel Execution Examples

```text
# Depois da Phase 2 completa, três frentes em paralelo:
Frente A (US1): T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017
Frente B (US2): T018 → T019 → T020 → T021 → T022 → T023
Frente C (US3): T024, T025, T026 [P entre si] → T027 → T028 → T029 → T030, T031 [P] → T032 → T033 → T034

# Dentro da Phase 8, testes e typecheck são paralelos entre si:
T044, T045, T046 [P] — specs de Playwright distintos
T048, T049 [P] — apps distintos
```

## Implementation Strategy

**MVP (entrega mínima demonstrável)**: Phase 1 + Phase 2 + Phase 3 (US1) + Phase 4 (US2) + Phase 5
(US3) — as 3 User Stories P1. Permite: staff cadastra Tema+Personagens+vídeo+tags no gerenciador,
cliente vê a vitrine completa com galeria de vídeo e elenco individual. US4 (P2) e US5 (P3) somam
valor incremental sem bloquear o lançamento do MVP.

**Incremental**: cada Phase 3-7 termina em um checkpoint testável isoladamente — pode virar um PR
próprio se o time preferir revisar em fatias menores em vez de um único merge final.
