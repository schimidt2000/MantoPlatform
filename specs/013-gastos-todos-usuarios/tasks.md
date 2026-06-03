# Tasks: Gastos extras abertos a todos, balanço só para admin

**Input**: `specs/013-gastos-todos-usuarios/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Permissão e filtragem (servidor)

- [ ] T001 [app/gastos/routes.py](../../app/gastos/routes.py) `index`: remover `abort(403)`; filtrar
      gastos por `created_by_id` quando não for super admin; calcular totais só para super admin
      (senão `None`).
- [ ] T002 [app/gastos/routes.py](../../app/gastos/routes.py) `novo`: remover `abort(403)` (qualquer
      autenticado registra; resto inalterado).

## Phase 2: Acesso e visibilidade (UI)

- [ ] T003 [app/templates/base.html](../../app/templates/base.html): link "Gastos Extras" passa a
      aparecer para qualquer usuário autenticado (remover gate SUPERADMIN).
- [ ] T004 [app/templates/gastos/index.html](../../app/templates/gastos/index.html): KPIs de balanço
      só sob `{% if is_superadmin %}`; título "Meus gastos" para não-admin; coluna "Autor" só para
      super admin.

## Phase 3: Polish

- [ ] T005 `ruff check` em `app/gastos/routes.py`.
- [ ] T006 Verificação no app real: comum registra e vê só os próprios sem totais; aprovar/rejeitar
      negado a não-admin (403); super admin vê totais + tudo + aprova (sem regressão).

## Dependencies
- T001/T002 independentes. T003/T004 independentes. Phase 3 após 1–2.

## Notes
- Sem migration. Aprovar/rejeitar/excluir e impacto no balanço inalterados.
