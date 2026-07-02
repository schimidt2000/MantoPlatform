# Tasks: Revisão de Vídeo Profissional Mobile-First

**Input**: Design documents from `/specs/104-revisao-video-mobile/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/routes.md, quickstart.md

**Tests**: não solicitados na spec e o projeto não possui suíte pytest — verificação é manual
via [quickstart.md](./quickstart.md) contra `manto_local` (Postgres), conforme prática do projeto.

**Organization**: tarefas agrupadas por user story; US1 (mobile-first) é o MVP.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Monolito Flask existente: código em `app/`, migrations em `migrations/versions/`,
templates em `app/templates/revisao/`.

---

## Phase 1: Setup

- [X] T001 Garantir cópia local atualizada e migrations aplicadas: rodar `.\scripts\db\refresh-local-db.ps1` (se banco velho) e `python -m flask db upgrade` com `DATABASE_URL` apontando para `manto_local` (ver `.local-db-url`); conferir head atual `e7b8c9d0f1a2` com `python -m flask db heads`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: schema e modelos que TODAS as stories usam (US2 e US3 dependem das colunas; US1 renderiza o JSON novo)

**⚠️ CRITICAL**: nenhuma story começa antes desta fase terminar

- [X] T002 Adicionar modelo `ReviewAssetVersion` em `app/models.py` (tabela `review_asset_versions`: asset_id FK+index, version_number, file_path, original_name, uploaded_by FK users nullable, created_at, expires_at nullable, file_removed default False; relationship `versions` no `ReviewAsset` com cascade delete-orphan e order_by version_number; property `is_available`) — conforme [data-model.md](./data-model.md)
- [X] T003 Estender `ReviewComment` em `app/models.py`: colunas `version_number` (Integer NOT NULL server_default "1"), `resolved_by` (FK users nullable), `resolved_at` (DateTime nullable); relationship `resolver`
- [X] T004 Escrever migration manual `migrations/versions/a3b4c5d6e7f8_review_versions_resolution.py` (`down_revision = "e7b8c9d0f1a2"`): create_table `review_asset_versions` + índice; add_column das 3 colunas em `review_comments`; backfill `UPDATE review_comments SET version_number = (SELECT version FROM review_assets WHERE review_assets.id = review_comments.asset_id)`; downgrade completo
- [X] T005 Aplicar a migration na cópia local (`python -m flask db upgrade` com `DATABASE_URL` = manto_local) e conferir backfill (`SELECT version_number, COUNT(*) FROM review_comments GROUP BY 1`)

**Checkpoint**: schema pronto — stories podem começar

---

## Phase 3: User Story 1 - Revisar vídeo pelo celular com experiência profissional (Priority: P1) 🎯 MVP

**Goal**: tela do material mobile-first estilo Vimeo — player no topo, comentários abaixo,
composer fixo com time code congelado no focus, timeline de marcadores, layout desktop em 2
colunas, identidade visual do sistema.

**Independent Test**: viewport 390×844 → abrir vídeo, comentar ancorado, navegar por time
codes; sem zoom/scroll horizontal; desktop ≥ 900px vira 2 colunas (roteiro US1 do
[quickstart.md](./quickstart.md)).

### Implementation for User Story 1

- [X] T006 [US1] Enriquecer `_comment_json` em `app/revisao/routes.py` com os campos novos do contrato ([contracts/routes.md](./contracts/routes.md)): `version_number`, `resolved_by_name`, `resolved_at`, `can_resolve` (regra FR-010: criador do espaço, super admin ou autor) e nova regra de `can_delete` (FR-011: só autor ou super admin)
- [X] T007 [US1] Reescrever `app/templates/revisao/asset.html` — estrutura e CSS mobile-first: coluna única, player full-width sticky no topo (vídeo/áudio) com timeline de marcadores, cabeçalho compacto (nome, badge versão, badge expiração), composer sticky no rodapé (chip de time code + textarea + botão), grid 2 colunas em `@media (min-width: 900px)`; alvos de toque ≥ 44px; só variáveis CSS do design system (`--accent`, `--panel`, `--line`, `--muted`, `--r-md`)
- [X] T008 [US1] JS do `asset.html` — comportamento estilo Vimeo: capturar `player.currentTime` e pausar no `focus` do textarea (time code congelado, edge case "tempo escorre"); chip clicável para descartar âncora; enviar com botão desabilitado + estado loading + erro amigável (Princípio V); time codes clicáveis fazem seek; marcadores na timeline desenhados após `loadedmetadata`; manter suporte imagem (pins), PDF (página) e áudio como hoje
- [X] T009 [US1] Verificação manual do roteiro US1 do [quickstart.md](./quickstart.md) contra `manto_local` (mobile 390×844 + desktop) e ajustes finos

**Checkpoint**: revisão mobile funcional e com cara do sistema — MVP entregável

---

## Phase 4: User Story 2 - Concluir comentários sem excluí-los (Priority: P2)

**Goal**: concluir registra quem/quando e fica visível a todos; abas Pendentes/Concluídos com
contadores (concluídos recolhidos); reabrir limpa registro; excluir restrito a autor/super
admin como ação secundária com confirmação.

**Independent Test**: com criador + revisor, concluir/reabrir/excluir conforme roteiro US2 do
[quickstart.md](./quickstart.md).

### Implementation for User Story 2

- [X] T010 [US2] Em `app/revisao/routes.py`: helper `_can_resolve(comment)` (criador do espaço, super admin ou autor) e `resolve_comment` atualizado — 403 para não autorizados; concluir grava `resolved_by`/`resolved_at`; reabrir limpa os três campos
- [X] T011 [US2] Em `app/revisao/routes.py`: restringir `delete_comment` a autor ou super admin (remover poder do criador do espaço), mantendo resposta `{"ok": true}`
- [X] T012 [US2] No `asset.html`: abas "Pendentes (n)" / "Concluídos (m)" com contadores, concluídos recolhidos por padrão; card de concluído exibe "Concluído por <nome> em <data>"; ações concluir/reabrir com feedback de loading; excluir como ação secundária discreta com `confirm()`; esconder ações conforme `can_resolve`/`can_delete` do JSON
- [X] T013 [US2] Verificação manual do roteiro US2 do [quickstart.md](./quickstart.md) com dois usuários contra `manto_local`

**Checkpoint**: fluxo de conclusão transparente funcionando junto com US1

---

## Phase 5: User Story 3 - Histórico de versões navegável (Priority: P3)

**Goal**: substituir arquivo preserva a versão anterior (snapshot); histórico lista versões
com data/autor; versão antiga abre em modo leitura com seus comentários; expiração/limpeza
cobrem snapshots.

**Independent Test**: substituir arquivo 2×, navegar o histórico, conferir comentários por
versão e snapshot no banco (roteiro US3 do [quickstart.md](./quickstart.md)).

### Implementation for User Story 3

- [X] T014 [US3] Em `app/revisao/routes.py`: `replace_asset` cria snapshot `ReviewAssetVersion` com os dados atuais do asset ANTES de sobrescrever e não chama mais `delete_file` no arquivo antigo; rastrear `uploaded_by` da nova versão (guardar quem enviou para o próximo snapshot — usar campo `uploaded_by` do snapshot com o autor do envio da versão snapshotada quando conhecido, senão None)
- [X] T015 [US3] Em `app/revisao/routes.py`: `add_comment` carimba `version_number = asset.version` e rejeita com 409 quando o request indica versão antiga; `list_comments` ganha query param `?v=` (default versão atual) filtrando `version_number`
- [X] T016 [US3] Em `app/revisao/routes.py`: `asset_view` ganha query param `?v=N` — carrega snapshot (404 se não existe), passa `viewing_version`, `version_file` e `history` ao template; sem `v` → modo normal com `history` para o seletor
- [X] T017 [US3] Em `app/revisao/routes.py` + `app/revisao/cleanup.py`: `finalize_asset`, `delete_asset` e `delete_space` removem também arquivos de snapshots não removidos; `cleanup_expired_review_files()` varre `review_asset_versions` expiradas (delete_file + file_removed=True), mantendo idempotência e docstring atualizada
- [X] T018 [US3] No `asset.html`: badge de versão abre painel/histórico (lista de versões com nº, data, autor, estado do arquivo); em versão antiga: banner "Você está vendo a versão N de M — voltar para a atual", player do snapshot (ou aviso de expirado), composer oculto, comentários da versão exibidos; link para voltar à atual
- [X] T019 [P] [US3] Em `app/templates/revisao/space.html`: card do material mostra contadores de comentários pendentes/concluídos e versão atual (ex.: "v3 · 2 pendentes · 5 concluídos")
- [X] T020 [US3] Verificação manual do roteiro US3 + regressão feature 090 do [quickstart.md](./quickstart.md) contra `manto_local` (substituir 2×, histórico, expiração via cleanup no shell, finalizar remove snapshots)

**Checkpoint**: as 3 stories funcionam de forma independente

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T021 Portões de qualidade: `mypy app/` sem erros novos nos arquivos tocados, `ruff format app/` e `ruff check app/` limpos; docstrings e type hints em todas as funções novas/alteradas
- [X] T022 Passada final de consistência visual nas 3 telas do módulo (list/space/asset) — espaçamentos múltiplos de 4px, zero cor hardcoded nova, textos pt-BR — e re-execução rápida do quickstart completo
- [X] T023 Commits atômicos por fase + merge da branch `104-revisao-video-mobile` em `main` e push (stage explícito, nunca `git add -A`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende de T001 — BLOQUEIA todas as stories (T002→T003 mesmo arquivo; T004 depende de T002/T003; T005 depende de T004)
- **US1 (Phase 3)**: depende da Phase 2 (JSON usa colunas novas)
- **US2 (Phase 4)**: depende da Phase 2; UI (T012) assenta sobre o template reescrito em US1
- **US3 (Phase 5)**: depende da Phase 2; UI (T018) assenta sobre o template reescrito em US1
- **Polish (Phase 6)**: depende de todas as stories

### User Story Dependencies

- **US1 (P1)**: independente após Foundational — MVP
- **US2 (P2)**: backend (T010–T011) independente; UI depende do template de US1
- **US3 (P3)**: backend (T014–T017) independente; UI depende do template de US1

### Parallel Opportunities

- T010–T011 (US2 backend) e T014–T017 (US3 backend) podem andar em paralelo com T007–T008
  (US1 template), pois tocam arquivos diferentes (`routes.py`/`cleanup.py` vs `asset.html`)
- T019 [P] (space.html) é paralelo a qualquer tarefa de `asset.html` ou `routes.py`

## Parallel Example: após Phase 2

```text
Dev A: T007–T008 (asset.html mobile-first)
Dev B: T010–T011 (permissões/conclusão em routes.py) → T014–T017 (versões em routes.py/cleanup.py)
Dev C: T019 (space.html)
```

## Implementation Strategy

**MVP first**: Phases 1–3 (US1) → validar no celular → US2 → US3 → Polish. Como o trabalho é
de um único agente, a ordem sequencial por prioridade é a executada; cada fase termina com
verificação no app real contra `manto_local` e um commit atômico.
