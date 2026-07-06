# Tasks — Referência por Faixa ou Valor Exato (111)

- [X] T001 `app/models.py`: `out_of_range` cobre modo exato; property `expected_label`
      (rótulo "R$ x – y" / "R$ x" / None)
- [X] T002 `app/gastos/routes.py`: `_parse_conta_form` lê `ref_mode` (faixa|exato) para
      variável — exato preenche `amount` e zera min/max; faixa zera `amount`; estimativa
      da soma usa o valor exato quando houver
- [X] T003 `app/templates/gastos/recorrentes.html`: radio Faixa/Exato (nova conta + modal
      editar), exibição da referência na coluna
- [X] T004 `app/templates/home.html`: alerta mostra "esperado R$ X" no modo exato
- [X] T005 Verificação funcional vs manto_local (exato fora/igual, faixa regressão, troca
      de modo, fixos intocados) + ruff
- [X] T006 Commit, merge em main, push
