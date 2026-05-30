# Tasks: Página de Gastos Especiais

**Input**: `specs/004-gastos-especiais/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Fundação (model + migration + config)

- [ ] T001 Model `SpecialExpense` em [app/models.py](../../app/models.py) (campos, relationships,
      propriedade `amount_brl`, constantes de categoria/status).
- [ ] T002 `UPLOAD_EXPENSES` em [app/config.py](../../app/config.py) + criar a pasta no factory
      ([app/__init__.py](../../app/__init__.py)).
- [ ] T003 Migration Alembic da tabela `special_expenses` (`flask db migrate` + `flask db upgrade`).

## Phase 2: US1/US2/US4 — Blueprint de gastos (P1)

- [ ] T004 Criar `app/gastos/__init__.py` e `app/gastos/routes.py` com `gastos_bp` e registrar
      em [app/__init__.py](../../app/__init__.py).
- [ ] T005 `GET /gastos/` (qualquer autenticado): lista + totais + flag super admin.
- [ ] T006 `POST /gastos/novo` (qualquer autenticado): valida valor (`_parse_brl`), salva
      comprovante, cria "pendente", AuditLog.
- [ ] T007 `POST /gastos/<id>/aprovar` e `/rejeitar` (super admin): muda status + aprovador/motivo + AuditLog.
- [ ] T008 `POST /gastos/<id>/excluir` (autor se pendente; super admin sempre).
- [ ] T009 Template [gastos/index.html](../../app/templates/gastos/index.html): formulário (com
      anexo) + lista com status/valor/categoria/autor/comprovante + ações condicionais; estado vazio.
- [ ] T010 Item de menu "Gastos Extras" em [base.html](../../app/templates/base.html) (qualquer autenticado).

## Phase 3: US3 — Integração financeira (P1)

- [ ] T011 Em `dashboard()` ([financeiro/routes.py](../../app/financeiro/routes.py)): somar gastos
      aprovados do mês (por `expense_date`) → `gastos_extras_mes`; abater do `lucro_liquido`; passar ao template.
- [ ] T012 Linha "Gastos Extras" em [financeiro/dashboard.html](../../app/templates/financeiro/dashboard.html).

## Phase 4: Polish

- [ ] T013 `ruff check` nos arquivos .py tocados.
- [ ] T014 Verificação no app real: criar gasto (qualquer user), aprovar (super admin), conferir
      lista + comprovante + linha no painel financeiro do mês; pendente/rejeitado NÃO contam.

## Dependencies
- T001→T003 (model antes da migration). T004 antes de T005-T009. T011 depende de T001.
- Aprovar/rejeitar (T007) e impacto financeiro (T011) dependem do model.

## Notes
- Reusar `_parse_brl`/`_fmt_brl`. Comprovante via `/uploads/expenses/<arquivo>`.
- Migration aditiva (nova tabela) — não toca tabelas existentes.
