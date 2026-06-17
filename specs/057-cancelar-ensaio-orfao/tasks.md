---
description: "Task list for feature 057 — Cancelar ensaio órfão"
---

# Tasks: Cancelar ensaio órfão (sem evento na agenda)

**Input**: Design documents from `specs/057-cancelar-ensaio-orfao/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cancel-ensaio.md, quickstart.md

**Tests**: Não solicitados e o projeto não possui suíte automatizada — verificação manual
via `quickstart.md`.

**Organização**: Tarefas por user story (US1–US3 de `spec.md`), ordem P1 → P1 → P2.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Confirmar que a rota `delete_ensaio` (`POST /events/<id>/delete-ensaio`) existe e
      já trata órfão (redireciona à home quando não há show pai), em `app/calendar/routes.py`
      — base reutilizada, sem rota nova

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Descobrir os ensaios órfãos para poder exibi-los/cancelá-los.

**⚠️ CRITICAL**: US1 depende desta query.

- [X] T002 Em `app/__init__.py` (rota home `/`), quando `show_ensaio`, montar
      `orphan_ensaios` = eventos `event_type == "ENSAIO"` com `parent is None` (FK nulo ou
      show removido), ordenados por `start_at` (inclui passados), e passá-los ao
      `render_template` (data-model.md, research.md itens 2–3)

**Checkpoint**: A home dispõe da lista de órfãos.

---

## Phase 3: User Story 1 - Cancelar um ensaio órfão (Priority: P1) 🎯 MVP

**Goal**: Localizar e cancelar, pela home, um ensaio cujo show pai não existe mais.

**Independent Test**: Com um ensaio órfão, abrir a home, vê-lo na seção de órfãos e
cancelá-lo; confirmar que some do sistema e da agenda.

### Implementation for User Story 1

- [X] T003 [US1] Em `app/templates/home.html`, no setor de Ensaios, adicionar a seção
      **"Ensaios sem show (órfãos)"** que lista `orphan_ensaios` (título + data/hora +
      observação) — visível só para `show_ensaio`; estado vazio omitido quando não houver
- [X] T004 [US1] Em `app/templates/home.html`, em cada órfão, adicionar o botão
      **"Cancelar ensaio"** (form POST para `/events/<id>/delete-ensaio`) com `confirm` antes
      de enviar (FR-001/FR-005)

**Checkpoint**: O ensaio órfão pode ser encontrado e cancelado pela home.

---

## Phase 4: User Story 2 - Botão de cancelar na própria página do ensaio (Priority: P1)

**Goal**: Abrir um ensaio e cancelá-lo ali mesmo, com ou sem show pai.

**Independent Test**: Abrir a página de um ensaio e cancelá-lo pelo botão; com pai volta ao
pai, sem pai volta à home.

### Implementation for User Story 2

- [X] T005 [US2] Em `app/templates/event_detail.html`, adicionar um bloco/banner visível
      quando `event.event_type == 'ENSAIO'` (e `show_ensaio`) com o botão **"Cancelar
      ensaio"** (form POST para `/events/<event.id>/delete-ensaio`) e `confirm` (FR-003/FR-005)
- [X] T006 [US2] Em `app/templates/event_detail.html`, no mesmo bloco, quando o ensaio tiver
      show pai, mostrar um link "Ver show" para o pai; quando órfão, deixar claro que não há
      show vinculado (sem erro) (FR-004 — apenas exibição; a rota já redireciona certo)

**Checkpoint**: Qualquer ensaio pode ser cancelado pela sua própria página.

---

## Phase 5: User Story 3 - Cancelar ensaio direto no painel da home (Priority: P2)

**Goal**: Cancelar ensaios na lista "Ensaios agendados" da home, ao lado de "Editar".

**Independent Test**: Na home, cancelar um ensaio sob um show e confirmar que some sem
afetar o show.

### Implementation for User Story 3

- [X] T007 [US3] Em `app/templates/home.html`, na lista "Ensaios agendados" (sob cada show),
      adicionar o botão **"Cancelar ensaio"** ao lado de "Editar" (form POST para
      `/events/<ens.id>/delete-ensaio`) com `confirm` (FR-008/FR-005)

**Checkpoint**: Cancelamento disponível também na lista de ensaios agendados.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T008 Executar `ruff check app/__init__.py` (corrigir o que for novo desta feature) e
      revisar visualmente os botões (confirmação presente, cores via variáveis CSS)
- [X] T009 Executar o `quickstart.md` (passos 1–5) no app real: cancelar órfão pela home,
      pela página do ensaio, pela lista de agendados; permissão; falha externa graciosa;
      confirmar que nenhum show é afetado

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: confirmação da rota existente.
- **Foundational (Phase 2)**: query de órfãos — BLOQUEIA US1.
- **US1 (Phase 3, P1)**: depende do Foundational. MVP (resolve o problema relatado).
- **US2 (Phase 4, P1)**: independente do Foundational (usa o próprio evento) — pode ir em
  paralelo a US1; toca outro arquivo (`event_detail.html`).
- **US3 (Phase 5, P2)**: usa a lista `scheduled_ensaio` já existente; toca `home.html`.
- **Polish (Phase 6)**: depende de tudo anterior.

### Parallel Opportunities

- US2 (T005–T006 em `event_detail.html`) pode ser feita em paralelo com US1/US3
  (`home.html` / `__init__.py`) — arquivos diferentes.
- Tarefas no mesmo `home.html` (T003, T004, T007) não são paralelas entre si.

---

## Implementation Strategy

### MVP (US1)

1. Foundational (query de órfãos).
2. US1 (seção de órfãos na home + cancelar).
3. **PARAR E VALIDAR**: quickstart passo 1 — resolve o caso do usuário.

### Incremental

1. Foundational → base.
2. US1 → MVP (cancelar órfão pela home), validar passo 1.
3. US2 → botão na página do ensaio, validar passo 2.
4. US3 → cancelar na lista de agendados, validar passo 3.
5. Polish → ruff + quickstart completo.

---

## Notes

- **Sem rota nova**: tudo reusa `delete_ensaio` (Princípio I). Sem migration.
- Ação destrutiva → confirmação obrigatória em todos os botões (Princípio V).
- Cancelar ensaio nunca afeta o show pai.
- Commit atômico após validação (Princípio IV).
