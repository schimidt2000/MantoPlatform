# Tasks: Editar avaliação de eventos (até 30 dias)

**Input**: `specs/010-editar-avaliacao/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Backend (P1)

- [ ] T001 Helper `_editable_rating_event_ids(talent) -> set[int]` em
      [app/talent_portal/routes.py](../../app/talent_portal/routes.py): avaliados (via
      `_rated_event_ids`) e terminados nos últimos 30 dias (coalesce end_at/start_at).
- [ ] T002 `home()` e `historico()` passam `editable_rating_event_ids` ao respectivo template.

## Phase 2: US1 — link "Editar avaliação" (P1)

- [ ] T003 [US1] [home.html](../../app/templates/portal/home.html) — no histórico recente, ao
      lado do "✓ Avaliado", link "Editar avaliação" quando `ev.id in editable_rating_event_ids`.
- [ ] T004 [US1] [historico.html](../../app/templates/portal/historico.html) — mesma adição.

## Phase 3: Polish

- [ ] T005 `ruff check` no .py tocado.
- [ ] T006 Verificação no app real: avaliado há 10d → "✓ Avaliado" + "Editar"; avaliado há 40d →
      só "✓ Avaliado"; abrir edição pré-preenche; salvar atualiza sem duplicar.

## Dependencies
- T001 → T002 → T003/T004.

## Notes
- Backend de edição (rate_event/submit_rating/rate.html) já existe — só falta o ponto de entrada.
- Janela de edição 30 dias pelo término. Sem migration.
