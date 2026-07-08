# Tasks — Data Customizável no Adiantamento de Salário (120)

- [X] T001 Migration (`salary_advances` += `advance_date`, backfill de `created_at::date`,
      depois NOT NULL), `down_revision = "a2b3c4d5e6f7"`, conferir unicidade do revision,
      upgrade no manto_local
- [X] T002 `app/models.py`: coluna `advance_date` em `SalaryAdvance`
- [X] T003 `app/financeiro/routes.py`: `salary_advance()` lê/valida `advance_date` (fallback
      hoje se vazio/inválido); serialização de `_advances` usa `advance_date`
- [X] T004 `app/templates/financeiro/pagamentos.html`: campo `<input type="date">` no modal
      (valor inicial hoje) + JS reseta o campo a cada abertura do modal
- [X] T005 Verificação funcional vs manto_local (cenários do plano) + ruff
- [X] T006 Commit, merge em main, push
