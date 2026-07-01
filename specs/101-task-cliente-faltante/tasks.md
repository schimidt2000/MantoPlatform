# Tasks: Task para o comercial completar clientes

**Feature**: 101-task-cliente-faltante | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> Sem migração. Testar contra `manto_local`. Espelha a tarefa "Sem valor de venda".

## Phase 1 — Query da tarefa (US1, P1) 🎯 MVP

- [ ] **T001** Em [app/__init__.py](../../app/__init__.py) `home()`: sob `show_comercial`, montar
  `events_sem_cliente` = `CalendarEvent` com `~CalendarEvent.event_clients.any()`, `start_at >=
  task_cutoff`, `group_leader_id IS NULL` e excluindo ENSAIO (`exclude_ensaios`), ordenado por
  `start_at`. Passar `events_sem_cliente` ao `render_template`. Cobre FR-001, FR-002, FR-004, FR-005.

## Phase 2 — UI (US1)

- [ ] **T002** Em [home.html](../../app/templates/home.html), bloco Comercial: seção **"Sem cliente"**
  (mesma aparência de "Sem valor de venda"), com badge, data e botão **Abrir**; incluir na contagem
  `_total_comercial` e na condição de "Nenhuma pendência comercial". Cobre FR-003, FR-006.

- [ ] **T003** Em [admin_settings.html](../../app/templates/admin_settings.html): ajustar o texto de
  ajuda da "Data de início do sistema" para citar também a tarefa de clientes faltantes.

## Phase 3 — Verificação

- [ ] **T004** Verificação contra `manto_local`: (a) evento a partir da data sem cliente aparece; (b)
  com cliente sai; (c) ENSAIO/satélite/antes-da-data não aparecem; (d) visível só p/ comercial. Cobre
  SC-001..SC-004.

- [ ] **T005** [P] `ruff` (se houver Python alterado), Jinja parse do `home.html`, boot do app.

## Dependências

- T001 → T002. T003/T004/T005 independentes ao final.

## Critério de pronto

- Tarefa "Sem cliente" na home comercial, com o corte da data de início; some ao associar cliente;
  ENSAIO/satélite/antes-da-data excluídos; só comercial vê. Checklist "Pronto" do CLAUDE.md.
