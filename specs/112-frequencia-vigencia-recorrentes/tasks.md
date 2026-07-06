# Tasks — Frequência e Vigência (112)

- [X] T001 Migration `a7b8c9d0e1f3` (frequency + start_date + end_date, backfill) e upgrade
      no manto_local; conferir unicidade do revision
- [X] T002 `app/models.py`: colunas + `FREQUENCIES`/`FREQUENCY_LABELS` +
      `occurrences_in_month(year, month)` + rótulo de vigência
- [X] T003 `app/gastos/routes.py`: `_parse_conta_form` (frequency/start/end, fim<início
      rejeitado); `ensure_recurring_entries` usa ocorrências; `recurring_alerts` pula 0;
      estimativa por frequência; ref_year/ref_month no contexto
- [X] T004 `app/templates/gastos/recorrentes.html`: selects/datas no form e no modal,
      coluna frequência/vigência, célula "fora do ciclo"
- [X] T005 Verificação funcional vs manto_local + ruff
- [X] T006 Commit, merge em main, push
