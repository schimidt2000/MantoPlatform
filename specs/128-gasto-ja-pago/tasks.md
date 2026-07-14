# Tasks — Gasto Extra Já Nasce Pago (128)

- [X] T001 Migration: `special_expenses` ganha `paid_at_creation` (Boolean, default
      False); checar colisão de revision-id
- [X] T002 `app/models.py`: coluna `SpecialExpense.paid_at_creation`
- [X] T003 `app/gastos/routes.py::novo()`: lê `paid_at_creation` do form (só quando
      `disbursement_type` está definido); grava `payment_status="pago"` +
      `paid_at_creation=True` quando marcado
- [X] T004 `app/templates/gastos/index.html`: checkbox "Já foi pago (não entra na
      planilha de pagamentos)" no formulário, visível para os dois tipos de desembolso
      (`toggleDisb()` estendido); badge "Pago (direto)" na lista quando
      `paid_at_creation`
- [X] T005 `app/financeiro/routes.py::pagamentos()`: filtro da query de `expenses` ganha
      `SpecialExpense.paid_at_creation.is_(False)`
- [X] T006 Verificação funcional vs manto_local (15/15): gasto com "já pago" marcado,
      aprovado, ausente da planilha do mês; gasto normal (sem marcar) continua
      aparecendo na planilha como antes; `payment_status`/`status` corretos em cada
      caso; badge "Pago (direto)" visível na lista; checkbox ignorada quando não há
      desembolso selecionado (FR-006); balanço financeiro soma os dois gastos
      aprovados corretamente. Ruff: 0 novo em todos os arquivos tocados (comparado
      contra worktree do `main`).
- [X] T007 Commit, merge em main, push
