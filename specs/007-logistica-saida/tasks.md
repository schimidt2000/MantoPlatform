# Tasks: Local de saída configurável + logística no convite

**Input**: `specs/007-logistica-saida/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Fundação (model + migration)

- [ ] T001 `CalendarEvent.departure_location` (String 300, nullable) em [app/models.py](../../app/models.py).
- [ ] T002 Migration à mão `departure_location` (down_revision = `a7b8c9d0e1f2`); `flask db upgrade`.

## Phase 2: US1 — Local de saída editável (P1)

- [ ] T003 [US1] `_handle_save_logistics` ([app/calendar/routes.py](../../app/calendar/routes.py)):
      ler `departure_location`; se mudou e há confirmados, somar a `logistics_changes`
      ("Local de saída: X → Y") e notificar; gravar (vazio → None).
- [ ] T004 [US1] [event_detail.html](../../app/templates/event_detail.html): campo "Local de saída"
      com valor padrão "Manto Produções"; ajustar label "Horário de saída da Manto" → "Horário de saída".

## Phase 3: US2 — Logística no convite (P1)

- [ ] T005 [US2] `send_invite_email` ([app/email_service.py](../../app/email_service.py)): helper
      `_logistics_rows(event)` que gera linhas de Saída (hora + local, default Manto) e Maquiagem
      (hora + local) só quando definidas; inserir no corpo do convite. Sem dados → sem linhas.

## Phase 4: Polish

- [ ] T006 `ruff check` nos .py tocados.
- [ ] T007 Verificação no app real:
      (a) logística: local default "Manto Produções"; trocar e salvar persiste; alteração notifica;
      (b) convite: e-mail de evento com saída+maquiagem inclui as linhas; sem logística, sem linhas.

## Dependencies
- T001 → T002 → T003. T005 independente (e-mail). T004 depende de T001 (campo).

## Notes
- Padrão "Manto Produções" aplicado na exibição (não backfill) — eventos antigos caem no padrão.
- Migration à mão (autogenerate quebrado — memória do projeto).
