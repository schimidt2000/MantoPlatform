# Implementation Plan: Referência por Faixa ou Valor Exato (111)

**Branch**: `111-referencia-faixa-ou-exato` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

## Summary

Conta variável ganha modo de referência: **faixa** (min–max, como hoje) ou **valor exato**
esperado. Sem migração: o valor exato reusa `RecurringExpense.amount` (coluna já existente,
até agora usada só pelos fixos). Modo derivado dos dados: `amount` preenchido = exato;
min/max preenchidos = faixa; salvar um modo zera os campos do outro. `out_of_range` passa a
cobrir o caso exato (`valor preenchido != amount`). UI: radio "Faixa / Valor exato" no
formulário de nova conta e no modal de edição; exibição da referência na lista, no alerta da
home e na soma estimada (exato entra pelo próprio valor).

## Technical Context

**Stack**: o mesmo da 110; **Storage**: nenhuma coluna nova — zero migration.

**Arquivos**: `app/models.py` (property `out_of_range` + helper de rótulo), `app/gastos/
routes.py` (`_parse_conta_form`: modo `ref_mode` p/ variável; estimativa da soma),
`app/templates/gastos/recorrentes.html` (radio + exibição), `app/templates/home.html`
(alerta mostra "esperado R$ X").

**Testing**: script test client vs manto_local — exato fora/igual (destaque sim/não), faixa
regressão, troca de modo na edição, fixos intocados.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Reusa coluna `amount` e todo o fluxo da 110; zero estrutura nova. |
| II. Padrões Python | ✅ Property com docstring atualizada. |
| III. Camadas | ✅ Regra no modelo (`out_of_range`), parse no helper do form. |
| IV. Não quebrar | ✅ Faixa e fixos idênticos; verificação cobre regressão explícita. |
| V. UI/UX | ✅ Radio com troca de campos visível; destaque igual ao existente. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | ✅ Mesmos inputs `brl-input`. |

**Gate: PASS.**

## Decisões

1. **Sem coluna nova**: variável com `amount` ≠ NULL = referência exata (campo era morto
   para variáveis); mutuamente exclusivo com min/max via limpeza no save. Evita migration e
   backfill.
2. **`out_of_range` no modo exato**: `amount preenchido != esperado` (comparação Decimal
   direta — centavos contam, é justamente o alerta de "veio diferente").
3. **Estimativa mensal**: variável exata entra pelo próprio valor (antes: teto da faixa).
