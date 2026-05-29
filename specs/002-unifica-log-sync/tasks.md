# Tasks: Unificar "Log Agenda" e "Sync Agenda"

**Input**: `specs/002-unifica-log-sync/` (spec.md, plan.md)

**Tests**: sem suíte automatizada — verificação manual no app real ao fim.

## Format: `[ID] [P?] [Story] Descrição`

---

## Phase 1: User Story 1 — Página única com sync + log (P1) 🎯 MVP

**Goal**: a página `/admin/sync` passa a mostrar também o log recente da agenda.

**Independent Test**: abrir `/admin/sync` e ver status de sync, botão de sincronizar e a
seção de log recente da agenda na mesma tela.

- [ ] T001 [US1] Em `sync_status()` ([app/admin/routes.py](../../app/admin/routes.py)),
      consultar as últimas ~20 entradas de `AuditLog` com `entity_type='agenda'` (mesma
      ordenação da rota `audit_logs`) e passar como `agenda_logs` ao template.
- [ ] T002 [US1] Em [app/templates/admin_sync.html](../../app/templates/admin_sync.html),
      adicionar a seção "Log recente da agenda" (tabela compacta: data, ator, ação,
      detalhe) com estado vazio, e link "Ver log completo →" para `/admin/logs?entity_type=agenda`.

**Checkpoint**: tudo da agenda numa página só.

---

## Phase 2: User Story 2 — Menu sem duplicação (P2)

- [ ] T003 [US2] Em [app/templates/base.html](../../app/templates/base.html), remover o item
      "Log Agenda" (linhas ~41-48) e ajustar o rótulo do item de sync para comunicar os
      dois papéis (ex.: "Sincronização" ou "Sync & Log Agenda"), mantendo rota/ícone.

---

## Phase 3: User Story 3 — Links antigos não quebram (P3)

- [ ] T004 [US3] Em `agenda_log()` ([app/calendar/routes.py](../../app/calendar/routes.py)),
      alterar o redirect para `admin.sync_status` (página unificada).

---

## Phase 4: Limpeza + Polish

- [ ] T005 Remover o template órfão `app/templates/agenda_log.html` (sem referências).
- [ ] T006 [P] Verificação: `ruff check` nos arquivos tocados; import + render de
      `/admin/sync` (200, com seção de log) e do redirect `/agenda/log` (302 → /admin/sync).

---

## Dependencies & Execution Order

- **T001 → T002** (dados antes do template).
- T003, T004, T005 independentes entre si (arquivos diferentes) — podem ir em qualquer ordem.
- T006 ao final.

## Notes
- Acesso preservado: `/admin/sync` é superadmin; "Log Agenda" também era. Sem mudança de permissão.
- Fora de escopo: reescrever a auditoria geral (`/admin/logs`).
