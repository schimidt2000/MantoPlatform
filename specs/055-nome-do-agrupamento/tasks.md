---
description: "Task list for feature 055 — Nome do agrupamento de eventos"
---

# Tasks: Nome do agrupamento de eventos

**Input**: Design documents from `specs/055-nome-do-agrupamento/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/group-name.md, quickstart.md

**Tests**: Não solicitados e o projeto não possui suíte automatizada — verificação manual
via `quickstart.md`, como nas features 051–054.

**Organização**: Tarefas por user story (US1–US3 de `spec.md`), ordem P1 → P1 → P2.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Confirmar head atual da migration (`flask db current` = `q3f4a5b6c7d8`) para usar
      como `down_revision` da nova migration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Campo de dados + propriedade de rótulo + migration — base de TODAS as stories.

**⚠️ CRITICAL**: Nenhuma user story funciona antes desta fase.

- [X] T002 Adicionar a coluna `group_name` (`String(200)`, nullable) em `CalendarEvent`, em
      `app/models.py` (data-model.md)
- [X] T003 Adicionar a propriedade `group_display_name` em `CalendarEvent`
      (`return self.group_name or self.title`), em `app/models.py` (research.md item 2)
- [X] T004 Escrever migration manual `migrations/versions/<rev>_group_name.py` adicionando a
      coluna via `batch_alter_table`, com `down_revision = q3f4a5b6c7d8`
- [X] T005 Aplicar a migration localmente (`python -m flask db upgrade`) e confirmar a coluna
      no schema do banco local (`instance/manto.db`)

**Checkpoint**: `group_name`/`group_display_name` existem e persistem.

---

## Phase 3: User Story 1 - Dar um nome ao agrupamento (Priority: P1) 🎯 MVP

**Goal**: Nomear o grupo ao agrupar e editá-lo depois; ver o nome na tela do evento.

**Independent Test**: Agrupar com nome; abrir principal/satélite e ver o nome; editar e
confirmar persistência.

### Implementation for User Story 1

- [X] T006 [US1] Em `app/calendar/routes.py`, fazer `_handle_group_events` ler
      `group_name` (opcional) e salvar `leader.group_name = group_name.strip() or None` ao
      concluir o agrupamento (contracts/group-name.md A)
- [X] T007 [US1] Em `app/calendar/routes.py`, implementar a ação `rename_group` e registrá-la
      em `_EVENT_ACTIONS`: valida RBAC (`_can_group_events`) e que o evento é principal
      (`is_group_leader`), seta `group_name` (vazio → `None`), grava `EventLog`, commita
      (contracts/group-name.md B)
- [X] T008 [US1] Em `app/templates/event_detail.html`, adicionar o campo opcional "Nome do
      grupo" no formulário de agrupar (feature 054)
- [X] T009 [US1] Em `app/templates/event_detail.html`, na seção do evento **principal**,
      exibir o nome do grupo e um formulário inline de edição (`action=rename_group`) com
      botão que desabilita ao enviar (anti-duplo-envio, Princípio V)
- [X] T010 [US1] Em `app/templates/event_detail.html`, no banner do evento **satélite**,
      exibir o nome do grupo (usa `group_leader.group_display_name`)

**Checkpoint**: Grupo pode ser nomeado/renomeado; nome visível no principal e nos satélites.

---

## Phase 4: User Story 2 - Home comercial mostra só o principal com o nome do grupo (Priority: P1)

**Goal**: Uma entrada por grupo na home comercial, rotulada pelo nome do grupo; satélites
fora das listas.

**Independent Test**: Grupo nomeado com cobrança pendente + satélites sem valor → home mostra
1 linha nomeada e nenhum satélite em "sem valor".

### Implementation for User Story 2

- [X] T011 [US2] Em `app/__init__.py` (rota home `/`), adicionar
      `CalendarEvent.group_leader_id.is_(None)` à query `events_sem_valor` para ocultar
      satélites (FR-005)
- [X] T012 [US2] Em `app/templates/home.html`, trocar `{{ ev.title }}` por
      `{{ ev.group_display_name }}` nas linhas de **cobranças pendentes** e de **eventos sem
      valor** da seção Comercial (FR-004)

**Checkpoint**: Home comercial mostra o grupo como uma entrada nomeada; satélites não poluem.

---

## Phase 5: User Story 3 - Balanços financeiros mostram o grupo como uma entrada nomeada (Priority: P2)

**Goal**: Tabela de eventos do painel financeiro exibe o grupo como 1 linha nomeada, sem
satélites; totais idênticos.

**Independent Test**: Grupo nomeado com cachês nos satélites → tabela mostra 1 linha com o
nome do grupo; satélites ausentes; KPIs idênticos.

### Implementation for User Story 3

- [X] T013 [US3] Em `app/financeiro/routes.py` (`dashboard()`), pular eventos satélites ao
      montar `events_data` (`if e.is_satellite: continue`) para não listá-los na tabela do
      período (FR-006); confirmar que `_compute_drg`/KPIs permanecem inalterados (FR-007)
- [X] T014 [US3] Em `app/templates/financeiro/dashboard.html`, usar `ev.group_display_name`
      na coluna "Evento" da tabela de eventos do período (FR-006)
- [X] T015 [US3] [P] Em `app/templates/vendas/pipeline.html`, usar `e.group_display_name` no
      rótulo do evento líder (consistência; satélites seguem com o selo da 054) — research.md
      item 6

**Checkpoint**: Balanço mostra o grupo como entrada nomeada única; cálculos sem regressão.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T016 Executar `ruff check` nos arquivos tocados (`app/models.py`,
      `app/calendar/routes.py`, `app/__init__.py`, `app/financeiro/routes.py`); corrigir o
      que for novo desta feature
- [X] T017 Executar o `quickstart.md` (passos 1–5) no app real, incluindo a equivalência dos
      KPIs financeiros (FR-007/SC-004) e a não-regressão de eventos não agrupados (FR-010)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: confirmação do head.
- **Foundational (Phase 2)**: BLOQUEIA todas as user stories (campo + propriedade + migration).
- **US1 (Phase 3, P1)**: depende do Foundational. MVP (nomear + ver).
- **US2 (Phase 4, P1)**: depende do Foundational e da propriedade (T003); independente da US1
  para exibir (usa fallback), mas o nome só aparece de fato após US1.
- **US3 (Phase 5, P2)**: depende do Foundational e da propriedade (T003).
- **Polish (Phase 6)**: depende de tudo anterior.

### Parallel Opportunities

- T015 (pipeline.html) é `[P]` — arquivo diferente das demais tarefas de US3.
- Tarefas no mesmo arquivo (`event_detail.html`: T008–T010; `home.html`: T012) não são
  paralelas entre si.

---

## Implementation Strategy

### MVP (US1 + US2)

1. Foundational (campo + propriedade + migration).
2. US1 (nomear/renomear + exibir no detalhe).
3. US2 (home comercial: 1 entrada nomeada, satélites ocultos).
4. **PARAR E VALIDAR**: quickstart passos 1–3.

### Incremental

1. Foundational → base.
2. US1 + US2 → MVP (nome + home), validar quickstart 1–3.
3. US3 → balanço financeiro nomeado, validar passo 4.
4. Polish → ruff + quickstart completo.

---

## Notes

- Migration manual (autogenerate quebrado por drift — memória do projeto).
- `group_display_name` é a fonte única do rótulo — não repetir `group_name or title` nos
  templates.
- Comitar a feature como um commit atômico após validação (Princípio IV).
