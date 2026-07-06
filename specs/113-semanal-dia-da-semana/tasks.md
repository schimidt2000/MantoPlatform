# Tasks — Conta Semanal: Dia da Semana (113)

- [X] T001 Migration `b8c9d0e1f2a4` (weekday + backfill ISODOW−1 p/ semanais) e upgrade
- [X] T002 `app/models.py`: coluna `weekday`, `WEEKDAY_LABELS`, `anchor_weekday`,
      `dia_label`; `occurrences_in_month` usa `anchor_weekday`
- [X] T003 `app/gastos/routes.py`: form exige weekday na semanal (due_day=1);
      `_first_weekday_date`; ensure usa 1ª ocorrência como due_date; alerts disparam na
      1ª ocorrência
- [X] T004 Templates: select dia da semana (nova + modal, via JS), rótulos `dia_label`
      (lista + home)
- [X] T005 Verificação vs manto_local + ruff
- [X] T006 Commit, merge em main, push
