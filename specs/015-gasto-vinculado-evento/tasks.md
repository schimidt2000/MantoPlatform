# Tasks: Vincular gasto extra a um evento

**Input**: `specs/015-gasto-vinculado-evento/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Dados (model + migration)

- [ ] T001 [app/models.py](../../app/models.py): `SpecialExpense.event_id` (FK nullable →
      calendar_events) + relationship `event`.
- [ ] T002 Migration à mão `e0f1a2b3c4d5` (down_revision `d9e0f1a2b3c4`): add_column `event_id` +
      índice `ix_special_expenses_event_id`; `flask db upgrade`.

## Phase 2: Backend (gastos)

- [ ] T003 [app/gastos/routes.py](../../app/gastos/routes.py): API `GET /gastos/api/eventos?date=`
      → eventos da data `[{id, label}]` (qualquer autenticado).
- [ ] T004 [app/gastos/routes.py](../../app/gastos/routes.py) `novo`: ler `event_id` opcional,
      validar existência, setar no gasto.
- [ ] T005 [app/gastos/routes.py](../../app/gastos/routes.py): `POST /gastos/<id>/vincular-evento`
      (super admin; "" remove vínculo; valida; log; commit).

## Phase 3: Página do evento

- [ ] T006 [app/calendar/routes.py](../../app/calendar/routes.py) `event_detail`: calcular
      `event_expenses` (aprovados do evento) + `event_expenses_total`; passar ao template.
- [ ] T007 [app/templates/event_detail.html](../../app/templates/event_detail.html): KPI "Gastos
      extras" + Lucro líquido = venda − cachês − gastos extras aprovados + lista (sob show_financeiro).

## Phase 4: Formulário e lista de gastos

- [ ] T008 [app/templates/gastos/index.html](../../app/templates/gastos/index.html): bloco opcional
      "Vincular a evento" (date + select via API) no formulário.
- [ ] T009 [app/templates/gastos/index.html](../../app/templates/gastos/index.html): coluna "Evento"
      na lista + editor inline (super admin) que usa a API e posta em `vincular-evento`.

## Phase 5: Polish

- [ ] T010 `ruff check` nos .py tocados.
- [ ] T011 Verificação no app real: migration up/down; criar com vínculo; aprovar → aparece no
      evento + Lucro abate; pendente/rejeitado não; super admin vincula antigo; não-admin → 403.

## Dependencies
- T001→T002→(T003,T004,T005). T006→T007. T008/T009 após T003/T005. Phase 5 ao fim.

## Notes
- Migration à mão (autogenerate quebrado). Coluna nullable — gastos atuais ficam sem vínculo.
- Só aprovados entram no evento e no lucro. Editar vínculo de gasto existente = só super admin.
