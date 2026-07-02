# Tasks: RevisÃ£o de VÃ­deo Profissional Mobile-First

**Input**: Design documents from `/specs/104-revisao-video-mobile/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/routes.md, quickstart.md

**Tests**: nÃ£o solicitados na spec e o projeto nÃ£o possui suÃ­te pytest â€” verificaÃ§Ã£o Ã© manual
via [quickstart.md](./quickstart.md) contra `manto_local` (Postgres), conforme prÃ¡tica do projeto.

**Organization**: tarefas agrupadas por user story; US1 (mobile-first) Ã© o MVP.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Monolito Flask existente: cÃ³digo em `app/`, migrations em `migrations/versions/`,
templates em `app/templates/revisao/`.

---

## Phase 1: Setup

**Purpose**: preparar ambiente de verificaÃ§Ã£o (nada de estrutura nova â€” mÃ³dulo jÃ¡ existe)

- [X] T001 Garantir cÃ³pia local atualizada e migrations aplicadas: rodar `.\scripts\db\refresh-local-db.ps1` (se banco velho) e `python -m flask db upgrade` com `DATABASE_URL` apontando para `manto_local` (ver `.local-db-url`); conferir head atual `e7b8c9d0f1a2` com `python -m flask db heads`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: schema e modelos que TODAS as stories usam (US2 e US3 dependem das colunas; US1 renderiza o JSON novo)

**âš ï¸ CRITICAL**: nenhuma story comeÃ§a antes desta fase terminar

- [X] T002 Adicionar modelo `ReviewAssetVersion` em `app/models.py` (tabela `review_asset_versions`: asset_id FK+index, version_number, file_path, original_name, uploaded_by FK users nullable, created_at, expires_at nullable, file_removed default False; relationship `versions` no `ReviewAsset` com cascade delete-orphan e order_by version_number; property `is_available`) â€” conforme [data-model.md](./data-model.md)
- [X] T003 Estender `ReviewComment` em `app/models.py`: colunas `version_number` (Integer NOT NULL server_default "1"), `resolved_by` (FK users nullable), `resolved_at` (DateTime nullable); relationship `resolver`
- [X] T004 Escrever migration manual `migrations/versions/a3b4c5d6e7f8_review_versions_resolution.py` (`down_revision = "e7b8c9d0f1a2"`): create_table `review_asset_versions` + Ã­ndice; add_column das 3 colunas em `review_comments`; backfill `UPDATE review_comments SET version_number = (SELECT version FROM review_assets WHERE review_assets.id = review_comments.asset_id)`; downgrade completo
- [X] T005 Aplicar a migration na cÃ³pia local (`python -m flask db upgrade` com `DATABASE_URL` = manto_local) e conferir backfill (`SELECT version_number, COUNT(*) FROM review_comments GROUP BY 1`)

**Checkpoint**: schema pronto â€” stories podem comeÃ§ar

---

## Phase 3: User Story 1 - Revisar vÃ­deo pelo celular com experiÃªncia profissional (Priority: P1) ðŸŽ¯ MVP

**Goal**: tela do material mobile-first estilo Vimeo â€” player no topo, comentÃ¡rios abaixo,
composer fixo com time code congelado no focus, timeline de marcadores, layout desktop em 2
colunas, identidade visual do sistema.

**Independent Test**: viewport 390Ã—844 â†’ abrir vÃ­deo, comentar ancorado, navegar por time
codes; sem zoom/scroll horizontal; desktop â‰¥ 900px vira 2 colunas (roteiro US1 do
[quickstart.md](./quickstart.md)).

### Implementation for User Story 1

- [X] T006 [US1] Enriquecer `_comment_json` em `app/revisao/routes.py` com os campos novos do contrato ([contracts/routes.md](./contracts/routes.md)): `version_number`, `resolved_by_name`, `resolved_at`, `can_resolve` (regra FR-010: criador do espaÃ§o, super admin ou autor) e nova regra de `can_delete` (FR-011: sÃ³ autor ou super admin)
- [X] T007 [US1] Reescrever `app/templates/revisao/asset.html` â€” estrutura e CSS mobile-first: coluna Ãºnica, player full-width sticky no topo (vÃ­deo/Ã¡udio) com timeline de marcadores, cabeÃ§alho compacto (nome, badge versÃ£o, badge expiraÃ§Ã£o), composer sticky no rodapÃ© (chip de time code + textarea + botÃ£o), grid 2 colunas em `@media (min-width: 900px)`; alvos de toque â‰¥ 44px; sÃ³ variÃ¡veis CSS do design system (`--accent`, `--panel`, `--line`, `--muted`, `--r-md`)
- [X] T008 [US1] JS do `asset.html` â€” comportamento estilo Vimeo: capturar `player.currentTime` e pausar no `focus` do textarea (time code congelado, edge case "tempo escorre"); chip clicÃ¡vel para descartar Ã¢ncora; enviar com botÃ£o desabilitado + estado loading + erro amigÃ¡vel (PrincÃ­pio V); time codes clicÃ¡veis fazem seek; marcadores na timeline desenhados apÃ³s `loadedmetadata`; manter suporte imagem (pins), PDF (pÃ¡gina) e Ã¡udio como hoje
- [X] T009 [US1] VerificaÃ§Ã£o manual do roteiro US1 do [quickstart.md](./quickstart.md) contra `manto_local` (mobile 390Ã—844 + desktop) e ajustes finos

**Checkpoint**: revisÃ£o mobile funcional e com cara do sistema â€” MVP entregÃ¡vel

---

## Phase 4: User Story 2 - Concluir comentÃ¡rios sem excluÃ­-los (Priority: P2)

**Goal**: concluir registra quem/quando e fica visÃ­vel a todos; abas Pendentes/ConcluÃ­dos com
contadores (concluÃ­dos recolhidos); reabrir limpa registro; excluir restrito a autor/super
admin como aÃ§Ã£o secundÃ¡ria com confirmaÃ§Ã£o.

**Independent Test**: com criador + revisor, concluir/reabrir/excluir conforme roteiro US2 do
[quickstart.md](./quickstart.md).

### Implementation for User Story 2

- [X] T010 [US2] Em `app/revisao/routes.py`: helper `_can_resolve(comment)` (criador do espaÃ§o, super admin ou autor) e `resolve_comment` atualizado â€” 403 para nÃ£o autorizados; concluir grava `resolved_by`/`resolved_at`; reabrir limpa os trÃªs campos
- [X] T011 [US2] Em `app/revisao/routes.py`: restringir `delete_comment` a autor ou super admin (remover poder do criador do espaÃ§o), mantendo resposta `{"ok": true}`
- [X] T012 [US2] No `asset.html`: abas "Pendentes (n)" / "ConcluÃ­dos (m)" com contadores, concluÃ­dos recolhidos por padrÃ£o; card de concluÃ­do exibe "ConcluÃ­do por <nome> em <data>"; aÃ§Ãµes concluir/reabrir com feedback de loading; excluir como aÃ§Ã£o secundÃ¡ria discreta com `confirm()`; esconder aÃ§Ãµes conforme `can_resolve`/`can_delete` do JSON
- [X] T013 [US2] VerificaÃ§Ã£o manual do roteiro US2 do [quickstart.md](./quickstart.md) com dois usuÃ¡rios contra `manto_local`

**Checkpoint**: fluxo de conclusÃ£o transparente funcionando junto com US1

---

## Phase 5: User Story 3 - HistÃ³rico de versÃµes navegÃ¡vel (Priority: P3)

**Goal**: substituir arquivo preserva a versÃ£o anterior (snapshot); histÃ³rico lista versÃµes
com data/autor; versÃ£o antiga abre em modo leitura com seus comentÃ¡rios; expiraÃ§Ã£o/limpeza
cobrem snapshots.

**Independent Test**: substituir arquivo 2Ã—, navegar o histÃ³rico, conferir comentÃ¡rios por
versÃ£o e snapshot no banco (roteiro US3 do [quickstart.md](./quickstart.md)).

### Implementation for User Story 3

- [X] T014 [US3] Em `app/revisao/routes.py`: `replace_asset` cria snapshot `ReviewAssetVersion` com os dados atuais do asset ANTES de sobrescrever e nÃ£o chama mais `delete_file` no arquivo antigo; rastrear `uploaded_by` da nova versÃ£o (guardar quem enviou para o prÃ³ximo snapshot â€” usar campo `uploaded_by` do snapshot com o autor do envio da versÃ£o snapshotada quando conhecido, senÃ£o None)
- [X] T015 [US3] Em `app/revisao/routes.py`: `add_comment` carimba `version_number = asset.version` e rejeita com 409 quando o request indica versÃ£o antiga; `list_comments` ganha query param `?v=` (default versÃ£o atual) filtrando `version_number`
- [X] T016 [US3] Em `app/revisao/routes.py`: `asset_view` ganha query param `?v=N` â€” carrega snapshot (404 se nÃ£o existe), passa `viewing_version`, `version_file` e `history` ao template; sem `v` â†’ modo normal com `history` para o seletor
- [X] T017 [US3] Em `app/revisao/routes.py` + `app/revisao/cleanup.py`: `finalize_asset`, `delete_asset` e `delete_space` removem tambÃ©m arquivos de snapshots nÃ£o removidos; `cleanup_expired_review_files()` varre `review_asset_versions` expiradas (delete_file + file_removed=True), mantendo idempotÃªncia e docstring atualizada
- [X] T018 [US3] No `asset.html`: badge de versÃ£o abre painel/histÃ³rico (lista de versÃµes com nÂº, data, autor, estado do arquivo); em versÃ£o antiga: banner "VocÃª estÃ¡ vendo a versÃ£o N de M â€” voltar para a atual", player do snapshot (ou aviso de expirado), composer oculto, comentÃ¡rios da versÃ£o exibidos; link para voltar Ã  atual
- [X] T019 [P] [US3] Em `app/templates/revisao/space.html`: card do material mostra contadores de comentÃ¡rios pendentes/concluÃ­dos e versÃ£o atual (ex.: "v3 Â· 2 pendentes Â· 5 concluÃ­dos")
- [X] T020 [US3] VerificaÃ§Ã£o manual do roteiro US3 + regressÃ£o feature 090 do [quickstart.md](./quickstart.md) contra `manto_local` (substituir 2Ã—, histÃ³rico, expiraÃ§Ã£o via cleanup no shell, finalizar remove snapshots)

**Checkpoint**: as 3 stories funcionam de forma independente

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T021 PortÃµes de qualidade: `mypy app/` sem erros novos nos arquivos tocados, `ruff format app/` e `ruff check app/` limpos; docstrings e type hints em todas as funÃ§Ãµes novas/alteradas
- [X] T022 Passada final de consistÃªncia visual nas 3 telas do mÃ³dulo (list/space/asset) â€” espaÃ§amentos mÃºltiplos de 4px, zero cor hardcoded nova, textos pt-BR â€” e re-execuÃ§Ã£o rÃ¡pida do quickstart completo
- [ ] T023 Commits atÃ´micos por fase + merge da branch `104-revisao-video-mobile` em `main` e push (stage explÃ­cito, nunca `git add -A`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependÃªncias
- **Foundational (Phase 2)**: depende de T001 â€” BLOQUEIA todas as stories (T002â†’T003 mesmo arquivo; T004 depende de T002/T003; T005 depende de T004)
- **US1 (Phase 3)**: depende da Phase 2 (JSON usa colunas novas)
- **US2 (Phase 4)**: depende da Phase 2; UI (T012) assenta sobre o template reescrito em US1
- **US3 (Phase 5)**: depende da Phase 2; UI (T018) assenta sobre o template reescrito em US1
- **Polish (Phase 6)**: depende de todas as stories

### User Story Dependencies

- **US1 (P1)**: independente apÃ³s Foundational â€” MVP
- **US2 (P2)**: backend (T010â€“T011) independente; UI depende do template de US1
- **US3 (P3)**: backend (T014â€“T017) independente; UI depende do template de US1

### Parallel Opportunities

- T010â€“T011 (US2 backend) e T014â€“T017 (US3 backend) podem andar em paralelo com T007â€“T008
  (US1 template), pois tocam arquivos diferentes (`routes.py`/`cleanup.py` vs `asset.html`)
- T019 [P] (space.html) Ã© paralelo a qualquer tarefa de `asset.html` ou `routes.py`

## Parallel Example: apÃ³s Phase 2

```text
Dev A: T007â€“T008 (asset.html mobile-first)
Dev B: T010â€“T011 (permissÃµes/conclusÃ£o em routes.py) â†’ T014â€“T017 (versÃµes em routes.py/cleanup.py)
Dev C: T019 (space.html)
```

## Implementation Strategy

**MVP first**: Phases 1â€“3 (US1) â†’ validar no celular â†’ US2 â†’ US3 â†’ Polish. Como o trabalho Ã©
de um Ãºnico agente, a ordem sequencial por prioridade Ã© a executada; cada fase termina com
verificaÃ§Ã£o no app real contra `manto_local` e um commit atÃ´mico.
