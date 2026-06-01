# Tasks: Avaliar qualquer evento elegível pelo histórico

**Input**: `specs/008-historico-review/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Backend — conjunto elegível (P1)

- [ ] T001 Helper `_rateable_event_ids(talent) -> set[int]` em
      [app/talent_portal/routes.py](../../app/talent_portal/routes.py) (termina ≤7 dias via
      coalesce(end_at,start_at) e não avaliado). Refatorar `home()` para reusá-lo em `events_to_rate`.
- [ ] T002 `home()` e `historico()` passam `rateable_event_ids` ao respectivo template.

## Phase 2: US1 — botão "Avaliar" no histórico (P1)

- [ ] T003 [US1] [home.html](../../app/templates/portal/home.html) — no "Histórico recente",
      botão "⭐ Avaliar" → `/portal/events/<ev.id>/rate` quando `ev.id in rateable_event_ids`.
- [ ] T004 [US1] [historico.html](../../app/templates/portal/historico.html) — mesmo botão nos
      itens elegíveis.

## Phase 3: US2 — texto do destaque (P2)

- [ ] T005 [US2] [home.html](../../app/templates/portal/home.html) — trocar título "Avalie seu
      último evento" por "Avalie seus eventos" (subtítulo já é plural condicional).

## Phase 4: Polish

- [ ] T006 `ruff check` no .py tocado.
- [ ] T007 Verificação no app real: dois eventos terminados ≤7 dias não avaliados → ambos com
      "Avaliar" no histórico; avaliado/fora da janela → sem botão; link leva à tela de avaliação.

## Dependencies
- T001 → T002 → T003/T004. T005 independente.

## Notes
- Reutiliza a tela de avaliação e a janela existentes. Sem migration.
