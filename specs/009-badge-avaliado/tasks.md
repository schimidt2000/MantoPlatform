# Tasks: Badge "✓ Avaliado" no histórico

**Input**: `specs/009-badge-avaliado/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Backend (P1)

- [ ] T001 Helper `_rated_event_ids(talent) -> set[int]` em
      [app/talent_portal/routes.py](../../app/talent_portal/routes.py); refatorar
      `_rateable_event_ids` para reusá-lo (DRY).
- [ ] T002 `home()` e `historico()` passam `rated_event_ids` ao respectivo template.

## Phase 2: US1 — badge "✓ Avaliado" (P1)

- [ ] T003 [US1] [home.html](../../app/templates/portal/home.html) — no histórico recente:
      se elegível → "⭐ Avaliar"; elif em `rated_event_ids` → badge "✓ Avaliado".
- [ ] T004 [US1] [historico.html](../../app/templates/portal/historico.html) — mesma lógica.

## Phase 3: Polish

- [ ] T005 `ruff check` no .py tocado.
- [ ] T006 Verificação no app real: evento avaliado → "✓ Avaliado" sem botão; elegível não
      avaliado → "⭐ Avaliar"; avaliado fora da janela → continua "✓ Avaliado".

## Dependencies
- T001 → T002 → T003/T004.

## Notes
- Badge independe da janela de 7 dias (rated_event_ids sem filtro de data).
- Reusa estilo pay-pago (verde) existente. Sem migration.
