# Implementation Plan: Frequência e Vigência (112)

**Branch**: `112-frequencia-vigencia-recorrentes` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

## Summary

`RecurringExpense` ganha `frequency` ("mensal"|"semanal"|"quinzenal"|"anual", default
mensal), `start_date` (NOT NULL, backfill = data de criação) e `end_date` (NULL = eterna).
Regra central no modelo: `occurrences_in_month(year, month) -> int` — 0 fora da vigência ou
fora do mês de aniversário (anual); semanal conta o dia-da-semana da data de início dentro
da interseção mês×vigência; quinzenal conta as janelas 1–15/16–fim que intersectam; mensal/
anual = 1. `ensure_recurring_entries` grava `amount × ocorrências`; `recurring_alerts` pula
contas com 0 ocorrências no mês. Form/modal ganham frequência + início + fim (fim < início
rejeitado). Migration manual `a7b8c9d0e1f3` (3 colunas + backfill).

## Technical Context

**Stack**: o da 110/111. **Storage**: 1 migration (3 colunas em `recurring_expenses`).

**Arquivos**: `app/models.py` (colunas + `occurrences_in_month` + labels), `app/gastos/
routes.py` (parse do form, ensure, alerts, estimativa, contexto ref_year/ref_month),
`app/templates/gastos/recorrentes.html` (selects/datas + coluna frequência/vigência +
"fora do ciclo"), migration nova.

**Testing**: script vs manto_local — semanal (valor × ocorrências, incl. início no meio do
mês), quinzenal (×2; ×1 se começa dia 16+), anual (só aniversário), vigência início futuro/
fim passado, fim<início rejeitado, regressão mensal (110/111).

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Mesma máquina de entries/alertas; regra nova concentrada em 1 método do modelo. |
| II. Padrões Python | ✅ Método com docstring/type hints; constantes de frequência no modelo. |
| III. Camadas | ✅ Regra de calendário no modelo; rotas só usam `occurrences_in_month`. |
| IV. Não quebrar | ✅ Default mensal + backfill início=criação ⇒ comportamento idêntico p/ dados existentes (regressão coberta). |
| V. UI/UX | ✅ Campos com defaults sensatos (mensal, início hoje, fim vazio=eterna); erro claro p/ fim<início; "fora do ciclo" visível. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | ✅ Sem novos formatos de valor. |

**Gate: PASS.**

## Decisões

1. **Ocorrências no modelo**: única fonte para ensure/alerts/tela — evita três cópias da
   regra de calendário.
2. **Amount do lançamento = valor × ocorrências**: DRE e planilha continuam lendo só o
   lançamento (nada muda a jusante).
3. **Backfill**: `frequency='mensal'`, `start_date=created_at::date` — FR-006 garantido no
   próprio upgrade.
4. **Anual sem rateio**: valor cheio no mês de aniversário (competência de caixa simples);
   estimativa mensal exibe ÷12 só como referência.
