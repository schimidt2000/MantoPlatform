# Tasks: Nota Fiscal obrigatória no gasto extra

**Input**: `specs/014-gastos-nota-fiscal/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Obrigatoriedade (servidor)

- [ ] T001 [app/gastos/routes.py](../../app/gastos/routes.py) `novo`: salvar o anexo junto das
      validações iniciais e, se ausente (`receipt_path is None`), `flash` de obrigatoriedade +
      redirect, sem criar o gasto.

## Phase 2: Rótulo e orientação (UI)

- [ ] T002 [app/templates/gastos/index.html](../../app/templates/gastos/index.html): campo de anexo
      vira "Nota Fiscal *" com `required` e orientação ("nota escaneada ou foto que mostre o valor
      dos produtos; comprovante/cupom fiscal não serve").
- [ ] T003 [app/templates/gastos/index.html](../../app/templates/gastos/index.html): cabeçalho da
      coluna da lista "Comprovante" → "Nota Fiscal".

## Phase 3: Polish

- [ ] T004 `ruff check` em `app/gastos/routes.py`.
- [ ] T005 Verificação no app real: sem anexo → bloqueado + aviso; com anexo → criado (pendente);
      rótulo e orientação visíveis; coluna renomeada.

## Dependencies
- T001 independente de T002/T003. Phase 3 após as anteriores.

## Notes
- Sem migration. Reaproveita `receipt_path`/`_save_receipt`. Gastos antigos não afetados.
