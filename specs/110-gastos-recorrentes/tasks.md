# Tasks — Gastos Recorrentes (110)

**Input**: plan.md, research.md, data-model.md, contracts/routes.md

## Phase 1: Setup

- [X] T001 Conferir head (`e5f6a7b8c9d0`) e unicidade do revision `f6a7b8c9d0e1`

## Phase 2: Foundational

- [X] T002 `app/models.py`: `RecurringExpense` + `RecurringExpenseEntry` (constantes de
      tipo/estado, unique conta+mês, relationships)
- [X] T003 Migration manual `f6a7b8c9d0e1_recurring_expenses.py` (2 tabelas + índices) e
      `flask db upgrade` no manto_local
- [X] T004 `app/gastos/routes.py`: guard `_require_financeiro_recorrentes` + helpers
      `ensure_recurring_entries(year, month)` e `recurring_alerts(today)`

## Phase 3: User Story 1 — variável: alerta, preencher, pagar (P1)

- [X] T005 Rotas: GET `/gastos/recorrentes` (lista + mês) e POST `nova`/`editar`/`toggle`/
      `excluir` (validações do contrato)
- [X] T006 Rotas: POST `<id>/preencher`, `<id>/pular`, `entry/<id>/pagar`, `entry/<id>/reabrir`
- [X] T007 Template `gastos/recorrentes.html`: grupos por tipo, status do mês, forms
      (nova/editar/preencher/pular/pagar), destaque fora da faixa, histórico por conta
- [X] T008 Home: `app/__init__.py` passa `recurring_alerts` (só FINANCEIRO/SUPERADMIN);
      `home.html` bloco "Contas recorrentes"
- [X] T009 Planilha: `_build_recurring_items()` em `app/financeiro/routes.py` + branch
      `"recurring"` no `set_payment_status`; conferir template pagamentos p/ o tipo novo
- [X] T010 `base.html`: link "Gastos Recorrentes" na seção Financeiro (guard existente)

## Phase 4: User Story 2 — fixos automáticos no balanço (P2)

- [X] T011 `ensure_recurring_entries` chamado em: recorrentes, home, pagamentos, dashboard
- [X] T012 Dashboard `/financeiro/`: variável `gastos_recorrentes` do período (soma
      `status != 'pulado'`), linha própria no template + inclusão no custo do DRE

## Phase 5: User Story 3 — organização (P3)

- [X] T013 Lista agrupada com soma mensal estimada por tipo; inativas destacadas;
      histórico de lançamentos por conta

## Phase 6: Polish & verificação

- [X] T014 Script de verificação funcional vs manto_local (cenários do quickstart)
- [X] T015 `ruff check` (sem erro novo) + `ruff format` no template/rotas novas se arquivo novo
- [X] T016 Commit atômico, merge em main, push
