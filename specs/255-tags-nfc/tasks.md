# Tasks: Tags NFC nas peças 3D com página pública por código

**Input**: Design documents from `/specs/255-tags-nfc/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/nfc-api.md, quickstart.md

**Tests**: A constituição (VIII, Test-First) exige o script de verificação funcional especificado/escrito ANTES do núcleo de negócio — ele nasce na fase Foundational apontando para endpoints que ainda não existem (falha primeiro, passa ao final de cada história).

**Organization**: por user story da spec (US1 página pública, US2 geração automática, US3 admin).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 Constantes do domínio em `app/constants.py`: `NFC_SUFFIX_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"`, `NFC_SUFFIX_LENGTH = 6`, `NFC_MAX_CODE_ATTEMPTS = 20`, `MANTO_INSTAGRAM_URL` (handle confirmado na T012)

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: bloqueia todas as histórias — modelo, migration e primitivas de criação são a base das três.

- [x] T002 Modelo `NfcTag` + coluna `Acervo3DItem.nfc_prefix` em `app/models.py` (seção Impressões 3D), conforme `data-model.md`: code único imutável, `sequence` com `UniqueConstraint(item_id, sequence)`, `event_id` nullable `ondelete="SET NULL"`, `is_active`, `notes`, `access_count`, `last_accessed_at`, `created_at`, relationships `item`/`event` e docstrings com o porquê (código eterno; conteúdo server-side)
- [x] T003 Migration Alembic manual `migrations/versions/<rev>_nfc_tags.py` com `down_revision = "f3a9c15d8b42"`: add_column `nfc_prefix` + create_table `nfc_tags` (índices e constraint única) + downgrade; aplicar no `manto_local` (`flask db upgrade`) e conferir com `\d nfc_tags`
- [x] T004 Núcleo puro `app/impressoes3d/nfc_ops.py` — primitivas compartilhadas: `_new_code(prefix)` (secrets + retry de colisão), `_next_sequence(item_id)`, `create_tags(item, quantity, event_id=None, commit=False)` (usadas pelas 3 histórias), `serialize_tag(tag)` e `NfcValidationError` no padrão de `Impressao3DValidationError`
- [x] T005 Script de verificação `scripts/verify_255_nfc.py` (padrão `verify_*`: login SÓ pela API contra `manto_local`, cenários 1–9 do `quickstart.md`, PASS/FAIL por cenário, limpeza ao final) — escrito AGORA, rodando e FALHANDO nos cenários de endpoint ainda não construídos (Test-First, constituição VIII)

**Checkpoint**: modelo migrado no manto_local, primitivas prontas, verify falhando pelos motivos certos.

## Phase 3: User Story 1 - Cliente encosta o celular e o portal se abre (Priority: P1) 🎯 MVP

**Goal**: `/nfc/<code>` público, mobile-first, com animação de portal, copy de boas-vindas e Instagram; código inválido/desativado → mesma página genérica.

**Independent Test**: seed de 1 tag via `create_tags` no verify → abrir `/nfc/<code>` sem sessão (viewport 375×812) e ver a página completa; `/nfc/XXXXXX` inventado → página genérica; cenários 6–7 do quickstart em PASS.

- [x] T006 [US1] `resolve_code(code)` em `app/impressoes3d/nfc_ops.py`: normaliza maiúsculas, tag ativa → payload `{product, campaign: None}` + contadores (commit tolerante a falha — métrica nunca derruba a página); inválida/inativa → payload genérico de MESMO shape (SC-006)
- [x] T007 [US1] Endpoint público `GET /api/nfc/<code>` em `app/api/nfc_read.py` (novo, SEM `api_login_required`, padrão `catalogo_read.py`), acrescentando `instagram_url` de `MANTO_INSTAGRAM_URL`; registrar import do módulo em `app/api/__init__.py`
- [x] T008 [US1] Entrada `NFC_PREFIX = "/nfc"` em `frontend/server.js` servindo `PUBLIC_DIST` sem reescrita (mecanismo idêntico e adjacente a `CADASTRO_PREFIX`, comentário explicando a URL eterna da tag)
- [x] T009 [US1] `frontend/apps/public/src/App.tsx`: generalizar `isCadastroSurface` → superfície de raiz (`/cadastro` OU `/nfc`), rota `/nfc/:code`, `WishlistFloat` suprimido também na superfície NFC
- [x] T010 [P] [US1] `frontend/apps/public/src/lib/nfc.ts`: interfaces `NfcResolution`/`NfcProduct` (espelho de `contracts/nfc-api.md`) + `useNfcResolution(code)` com `apiFetch`
- [x] T011 [US1] `frontend/apps/public/src/pages/NfcPage.tsx`: mobile-first 320–430px, animação de portal (Framer Motion 300–350ms, fases encadeadas, fallback `useReducedMotion`), identidade Manto, copy de boas-vindas (lapidar a partir de "A magia da Manto também na sua casa — em breve, um portal se abrirá aqui"), foto/nome do produto via `assetUrl()` quando houver, link Instagram (toque ≥ 44px); modo genérico quando `product: null`
- [x] T012 [US1] Confirmar o handle real do Instagram da Manto (site público mantoproducoes.com.br / usuário) e fixar em `MANTO_INSTAGRAM_URL`; se inconfirmável, deixar placeholder claro e reportar ao usuário antes do deploy
- [x] T013 [US1] Verificação: cenários 6–7 do verify em PASS + conferência visual mobile (dev `npm run dev:public`, viewport 375×812 e 320px, reduced motion) + `npx tsc --noEmit` limpo em `frontend/apps/public`

**Checkpoint**: página pública no ar em dev, genérica e personalizada, aprovada em mobile.

## Phase 4: User Story 2 - O código nasce sozinho quando o show é contratado (Priority: P2)

**Goal**: presente 3D de item com `nfc_prefix` → tags automáticas por unidade, associadas ao evento; aumento de quantidade completa, redução/remoção nunca apaga.

**Independent Test**: cenários 2–3 e 8 do quickstart (criar presente qty 2 → 2 tags; qty 3 → +1; qty 1 → mantém 3; item sem prefixo → zero tags).

- [x] T014 [US2] `sync_event_gift_tags(event, item)` em `app/impressoes3d/nfc_ops.py`: alvo = `sum(quantity)` dos presentes do item no evento; existentes = count `(event_id, item_id)`; cria só a diferença positiva via `create_tags` (sem commit — mesma transação do chamador); item sem `nfc_prefix` → no-op
- [x] T015 [US2] Chamar o sync em `add_event_gift` e `update_event_gift` (`app/impressoes3d/impressoes3d_ops.py`) antes do commit (em `update`, também quando `item_id` trocar para item NFC); `delete_event_gift` intocado (nunca apaga tags)
- [x] T016 [US2] Campo `nfc_prefix` no Acervo: aceitar no create/update de `app/api/impressoes3d_write.py` (normalizado: trim, maiúsculas, sem `-`; vazio = NULL) e expor em `serialize_acervo_item` (`app/impressoes3d/impressoes3d_ops.py`)
- [x] T017 [US2] Verificação: cenários 2–3 e 8 do verify em PASS (inclui unicidade de código e `sequence` contínua por item)

**Checkpoint**: contratou show com luminária → tags existem sem ação manual.

## Phase 5: User Story 3 - Equipe gerencia as tags no ERP (Priority: P3)

**Goal**: tela "Tags NFC" em `/3d/tags` — nº sequencial em destaque, lote, associar evento, ativar/desativar, copiar link; sem exclusão.

**Independent Test**: cenários 4–5 do quickstart + roteiro visual do admin (lote de 5, associar, desativar → página pública genérica).

- [x] T018 [US3] Ops de gestão em `app/impressoes3d/nfc_ops.py`: `list_tags()` (joinedload item/event/event_clients, ordenada por item + sequence), `generate_batch(item, quantity)` (commit + audit), `update_tag(tag, event_id=..., is_active=..., notes=...)` (sentinela p/ event_id null, commit + audit); `serialize_tag` ganha `client_name` via `client_of_event` (reuso de `app/api/agenda_read.py`)
- [x] T019 [US3] Endpoints admin: `GET /api/3d/nfc` em `app/api/nfc_read.py` + `POST /api/3d/nfc/lote` e `PATCH /api/3d/nfc/<id>` em `app/api/nfc_write.py` (novo) — RBAC via `require_3d_access` (reuso), validação → `json_error(fields=...)`, import em `app/api/__init__.py`
- [x] T020 [P] [US3] `frontend/apps/internal/src/lib/nfc.ts`: tipos do contrato + `useNfcTags`/`useGerarLote`/`useAtualizarTag` (TanStack Query, invalidação da key `["nfc-tags"]`); adicionar `nfc_prefix` ao tipo do acervo em `frontend/apps/internal/src/lib/impressoes3d.ts`
- [x] T021 [US3] `frontend/apps/internal/src/pages/Tags3DPage.tsx`: tabela com **Nº em destaque** (rótulo físico), código, produto (miniatura quadrada), evento, cliente, situação, acessos, copiar link (`${origin}/nfc/${code}`, feedback de copiado); dialog "Gerar lote" (combobox de item NFC + quantidade); associar/trocar evento via combobox pesquisável de eventos já existente no ERP; switch ativar/desativar com loading; SEM ação de excluir; Framer Motion nas transições
- [x] T022 [US3] Rota `/3d/tags` em `frontend/apps/internal/src/App.tsx` + entrada "Tags NFC" na seção 3D de `frontend/apps/internal/src/lib/navigation.tsx`
- [x] T023 [US3] Campo "Prefixo NFC" (opcional, com hint do formato do código) no formulário de peça do Acervo em `frontend/apps/internal/src/pages/Acervo3DPage.tsx`
- [x] T024 [US3] Verificação: cenários 4–5 do verify em PASS + roteiro visual admin do quickstart + `npx tsc --noEmit` limpo em `frontend/apps/internal`

**Checkpoint**: as três histórias funcionam de ponta a ponta.

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T025 Verify completo (cenários 1–9) em PASS contra `manto_local` + `ruff check` nos arquivos Python tocados + `tsc` limpo nos dois apps
- [x] T026 [P] Documentação viva: `docs/01_SISTEMA_E_BANCO.md` (tabela/coluna/rotas/RBAC), `docs/02_MAPA_DE_PAGINAS_E_UX.md` (`/nfc/<code>` público + `/3d/tags`), entrada nova no topo de `docs/03_HISTORICO_MUTACOES.md` (migration, motivação, regras, pegadinhas)
- [x] T027 `/speckit-converge` para fechar gaps entre spec/plan/tasks/código

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2)** bloqueia tudo: T002 → T003 → T004; T005 depois de T004 (usa `create_tags` p/ seed).
- **US1 (T006–T013)**: só depende da Foundational. MVP.
- **US2 (T014–T017)**: só depende da Foundational (independente de US1 — testável pela API/verify).
- **US3 (T018–T024)**: depende da Foundational; integra com US1 (link copiado abre a página) mas testável sozinha pela API.
- **Polish (T025–T027)**: depois de tudo.

### Parallel Opportunities

- T010 ∥ T008/T009 (arquivos distintos); T020 ∥ T018/T019; T026 ∥ T025.
- US1, US2 e US3 são paralelizáveis entre si após a Foundational (nesta sessão: sequencial P1 → P2 → P3).

## Implementation Strategy

MVP = Foundational + US1 (página pública com tag semeada). Depois US2 (automação) e US3 (admin), validando cada checkpoint com o verify + tsc antes de seguir. Commits atômicos por fase/história no padrão `feat(255): ...`.

## Phase 7: Convergence

- [x] T028 Corrigir o comando de verificação em `specs/255-tags-nfc/quickstart.md` para o caminho real `specs/255-tags-nfc/verify_255.py` (o script saiu de `scripts/` porque `scripts/db` é gitignorado) per quickstart.md (partial)
