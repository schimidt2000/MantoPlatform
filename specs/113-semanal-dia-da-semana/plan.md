# Implementation Plan: Conta Semanal — Dia da Semana (113)

**Branch**: `113-semanal-dia-da-semana` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

## Summary

`RecurringExpense` ganha `weekday` (Integer 0–6, 0=segunda, nullable — usado só na
frequência semanal). Migration `b8c9d0e1f2a4` faz backfill das semanais existentes com o dia
da semana da `start_date` (ISODOW−1). Modelo: `anchor_weekday` (weekday ?? start_date) usado
por `occurrences_in_month`; `dia_label` ("dia N" / "toda semana (quarta)"). Rotas: form
exige weekday na semanal (due_day gravado como 1); `ensure_recurring_entries` usa a primeira
ocorrência do dia da semana como `due_date`; `recurring_alerts` dispara na primeira
ocorrência (em vez de `due_day`). Templates: select de dia da semana aparece/some via JS
(nova conta + modal), rótulos usam `dia_label` (lista e home).

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Mesma máquina; 1 coluna + 2 helpers no modelo. |
| II. Padrões Python | ✅ Constante `WEEKDAY_LABELS`; docstrings. |
| III. Camadas | ✅ Regra no modelo; rotas usam helpers. |
| IV. Não quebrar | ✅ Backfill das semanais preserva comportamento (mesma âncora); demais frequências intocadas; regressão coberta. |
| V. UI/UX | ✅ Campo troca na hora ao mudar frequência; erro claro sem weekday. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | ✅ N/A. |

**Gate: PASS.**

## Decisões

1. **Coluna própria `weekday`** (não sobrecarregar `due_day` 1–31 com 0–6): semântica limpa;
   `due_day=1` gravado nas semanais só para satisfazer o NOT NULL (não exibido).
2. **Alerta semanal** = primeira ocorrência do dia da semana no mês∩vigência (helper
   `_first_weekday_date`), também usada como `due_date` do lançamento fixo.
3. **Fallback**: `anchor_weekday` cai no dia da semana da `start_date` p/ linhas antigas
   sem `weekday` (robustez além do backfill).
