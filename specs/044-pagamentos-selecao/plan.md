# Implementation Plan: Seleção em massa correta na Planilha de Pagamentos

**Branch**: `044-pagamentos-selecao` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)

## Summary

Sem migration. Causas raiz:
1. JS `select-all` marca todos os `.row-check`, inclusive de linhas escondidas pelo filtro
   (`applyFilter` usa display:none).
2. JS `bulkSubmit` mapeia tudo que não é salário para `role_ids` — gasto (id numérico) era
   aplicado em `EventRole.query.get(id)` (não muda o gasto e PODE alterar/excluir cachê errado).
3. Template pula o checkbox para `item.type == 'commission'` e o backend bulk não conhece
   comissões.

## Design

### `app/templates/financeiro/pagamentos.html`
- Checkbox também para comissão (`data-type="commission"`, `data-id="sellerId:YYYY-MM"`).
- `bulkSubmit`: mapa explícito `{cache: role_ids, salary: salary_ids, expense: expense_ids,
  commission: commission_ids}`.
- `select-all`: marca/desmarca só checkboxes de linhas visíveis (`tr.style.display !== 'none'`).
- `applyFilter`: desmarca checkbox de linha que ficou escondida + `updateBulkBar()`.

### `app/financeiro/routes.py` — `bulk_payment_action`
- Lê também `expense_ids` e `commission_ids`.
- Ação de status: expenses → `SpecialExpense.payment_status` (audit); commissions → mesmo
  comportamento do `set_payment_status` (target pago/a_pagar + paid_at) — só para ação
  `pago`/`nao_pago`; `no_banco` em comissão é ignorado e contado.
- Ação delete: só roles/salaries; expenses/commissions ignorados e contados.
- Flash resumo: "N itens atualizados/excluídos" + "M ignorados (...)" quando houver.

## Verificação
- ruff (sem novos) + boot.
- Test client (seeds temporários): bulk status em expense muda SpecialExpense e NÃO muda
  EventRole de id igual; bulk pago em commission_ids marca CommissionPayments do período;
  delete com expense selecionado não exclui gasto (flash de ignorado) e exclui cachê/salário;
  template tem checkbox em linha de comissão. Select-all visível é comportamento de JS — coberto
  por inspeção do HTML/JS gerado (asserts de presença das mudanças).

## Project Structure
```text
app/templates/financeiro/pagamentos.html  # checkbox comissão + JS select-all/bulkSubmit/applyFilter
app/financeiro/routes.py                  # bulk_payment_action: expense_ids/commission_ids + flashes
```

## Fora de escopo
- Excluir gastos/comissões pela planilha (pertencem aos seus módulos).
