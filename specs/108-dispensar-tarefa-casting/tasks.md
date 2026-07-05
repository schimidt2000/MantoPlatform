# Tasks: Dispensar Tarefa de Casting Pendente

**Input**: Design documents from `/specs/108-dispensar-tarefa-casting/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/routes.md, quickstart.md

**Tests**: verificação via script de test client contra `manto_local` (quickstart) — sem
suíte pytest no projeto (constituição v1.3.0).

**Organization**: US1 (dispensar) é o MVP; US2 (restaurar) estende o mesmo modelo/UI.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Monolito Flask: `app/models.py`, `app/calendar/routes.py`, `app/__init__.py`,
`app/templates/home.html`, `migrations/versions/`.

---

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` atualizado e no head `a3b4c5d6e7f8` (`python -m flask db heads` com `DATABASE_URL` da cópia local)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: schema que as duas stories usam

- [X] T002 Adicionar `dismissed_at` (DateTime, nullable) e `dismissed_by` (Integer FK `users.id`, nullable) em `EventRole` (`app/models.py`); relationship `dismisser = db.relationship("User", lazy=True, foreign_keys=[dismissed_by])` — conforme [data-model.md](./data-model.md)
- [X] T003 Escrever migration manual `migrations/versions/<hash>_event_role_dismiss.py` (`down_revision = "a3b4c5d6e7f8"`): `add_column` das 2 colunas em `event_roles`; downgrade remove ambas
- [X] T004 Aplicar a migration na cópia local (`python -m flask db upgrade`) e conferir `python -m flask db heads`

**Checkpoint**: schema pronto

---

## Phase 3: User Story 1 - Super admin dispensa uma tarefa de casting obsoleta (Priority: P1) 🎯 MVP

**Goal**: dispensar um cargo pendente direto da home; ele some da lista/contadores e a sync
nunca mais o recria.

**Independent Test**: roteiro US1 do [quickstart.md](./quickstart.md) (itens 1, 3, 5, 6, 7, 8).

### Implementation for User Story 1

- [X] T005 [US1] Em `app/calendar/routes.py`: rota `POST /roles/<int:role_id>/dismiss` — `_is_superadmin()` (403 se não), busca o cargo (`get_or_404`), rejeita com flash se `talent_id` preenchido (FR-009), idempotente se já dispensado, senão seta `dismissed_at`/`dismissed_by`, grava `EventLog`, commit, flash de sucesso, redireciona para `request.referrer` (fallback `url_for("home")`) — conforme [contracts/routes.md](./contracts/routes.md)
- [X] T006 [US1] Em `app/__init__.py` (rota `/`): acrescentar `EventRole.dismissed_at.is_(None)` aos filtros de `pending_casting`, `total_casting` e `done_casting` (research.md R6)
- [X] T007 [US1] Em `app/templates/home.html`, seção Casting (bloco `pending_casting`, por volta da linha 102): adicionar botão "Dispensar" por linha, visível só quando `is_superadmin`, form `POST /roles/{{ r.id }}/dismiss` com `confirm()` (proteção de duplo envio já é global desde a feature 107 — sem JS adicional)
- [X] T008 [US1] Verificação US1: script test client cobrindo RBAC 403, dispensa remove da lista/contadores, rejeição quando cargo tem talento, idempotência no duplo clique, e o **cenário central** — rodar a função de sync do módulo após dispensar e confirmar que o cargo não é recriado/alterado (roteiro completo do [quickstart.md](./quickstart.md))

**Checkpoint**: cargo obsoleto sai de vez das tarefas pendentes — MVP entregável

---

## Phase 4: User Story 2 - Super admin reverte uma dispensa feita por engano (Priority: P2)

**Goal**: listar cargos dispensados do setor e restaurar um deles.

**Independent Test**: roteiro US2 do [quickstart.md](./quickstart.md) (itens 2, 4).

### Implementation for User Story 2

- [X] T009 [US2] Em `app/calendar/routes.py`: rota `POST /roles/<int:role_id>/restore` — mesmo padrão de RBAC/idempotência de T005; limpa `dismissed_at`/`dismissed_by`; `EventLog` de restauração; redireciona para `request.referrer`
- [X] T010 [US2] Em `app/__init__.py` (rota `/`): quando `is_superadmin`, montar `dismissed_casting` (query em [contracts/routes.md](./contracts/routes.md)) e passar ao template; lista vazia (nem a query roda) quando não superadmin
- [X] T011 [US2] Em `app/templates/home.html`, seção Casting: sub-bloco "🗂 N dispensada(s)" (só `is_superadmin and dismissed_casting`) listando personagem, evento, `dismisser.name`/data, botão "Restaurar" (`POST /roles/{{ r.id }}/restore`)
- [X] T012 [US2] Verificação US2: script test client — restaurar volta o cargo a `pending_casting`/contadores; sub-bloco lista corretamente quem/quando; idempotência ao restaurar 2x

**Checkpoint**: dispensa totalmente reversível e auditável

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T013 `ruff check app/calendar/routes.py app/models.py app/__init__.py`; docstrings/type hints nas rotas novas; conferir no app real (viewport padrão — tela interna, não é superfície pública)
- [X] T014 Commits atômicos por story + merge da branch `108-dispensar-tarefa-casting` em `main` + push (stage explícito)

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)**: bloqueia as duas stories (T002→T003→T004 sequencial, mesmo schema)
- **US1 (Phase 3)**: depende da Phase 2; T005 e T006 tocam arquivos diferentes ([P] entre si); T007 depende de T005/T006 (usa a rota e os dados); T008 fecha
- **US2 (Phase 4)**: depende da Phase 2 e reusa a rota de T005 como referência; T009/T010 [P] entre si; T011 depende de ambos; T012 fecha
- **Polish (Phase 5)**: depende de tudo

### Parallel Opportunities

- T005 (routes.py) ∥ T006 (`__init__.py`) — arquivos diferentes
- T009 (routes.py) ∥ T010 (`__init__.py`) — arquivos diferentes

## Implementation Strategy

Sequencial por prioridade: Setup → Foundational → US1 (MVP, dispensar) → US2 (restaurar) →
Polish. Verificação test client a cada checkpoint; commit por fase.
