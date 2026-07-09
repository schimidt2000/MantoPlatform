# Tasks — Pagamento Programado (Gastos Recorrentes) (121)

- [X] T001 Migration (`recurring_expense_entries`: drop `uq_recurring_entry_month`),
      `down_revision = "c4d5e6f7a8b9"`, conferir unicidade do revision, upgrade no
      manto_local
- [X] T002 `app/models.py`: `RecurringExpense.TYPES`/`TYPE_LABELS` += "programado";
      propriedade de resumo das parcelas (contagem + total + próxima data)
- [X] T003 `app/gastos/routes.py`: `_parse_programado_form()` + rota `POST
      /gastos/recorrentes/programado/nova` (cria a conta + 1 `RecurringExpenseEntry` por
      data, status `a_pagar`); `_estimate()` retorna 0 para "programado"
- [X] T004 `app/gastos/routes.py`: rota `POST /gastos/recorrentes/entry/<id>/excluir-parcela`
      (só parcela não paga de conta "programado")
- [X] T005 `app/templates/gastos/recorrentes.html`: seção "Pagamentos programados"
      (formulário com linhas dinâmicas de data+valor, mesmo/individual; listagem de cada
      compromisso com todas as parcelas); excluir "programado" dos loops genéricos de
      KPI/tabela
- [X] T006 Verificação funcional vs manto_local (cenários do plano) + ruff
- [X] T007 Commit, merge em main, push
