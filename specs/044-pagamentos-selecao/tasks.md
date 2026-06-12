# Tasks: Seleção em massa na Planilha de Pagamentos

**Input**: `specs/044-pagamentos-selecao/`
**Tests**: boot + ruff + test client. Sem migration.

- [x] T001 Backend `bulk_payment_action`: expense_ids + commission_ids; delete só cachê/salário;
      flash resumo com ignorados.
- [x] T002 Template: checkbox na linha de comissão.
- [x] T003 JS: bulkSubmit com mapa por tipo; select-all só visíveis; applyFilter desmarca ocultas.
- [x] T004 Verificação (US1–US3) + commit.

## Dependencies
- T001 → T004; T002/T003 paralelos.
