# Pesquisa — 353 Gasto extra parcelado

Mapa dos consumidores da Planilha feito por leitura do código em 17/11 (agente de leitura, achados com arquivo:linha).

## R1. Como o gasto chega à Planilha

Um item por gasto, `type "expense"`, `id = SpecialExpense.id`, `date = expense_date`
(`app/financeiro/routes.py:927-943`), a partir de `_pagamentos_gastos_entre` (`:754-770`). A API
(`financeiro_read.py:687-783`) e os atrasados (`atrasados_ops.py:80-84`) usam essa função; a página Jinja
(`routes.py:1159-1165`) tem cópia própria e não é servida em produção (`frontend/server.js` não repassa `/financeiro/*`).

## R2. Escrita na Planilha

- Set-status (`financeiro_write.py:53-208`): ramo por `item_type`; **tipo desconhecido cai no `EventRole` de mesmo id**
  (`:194-208`). Decisão: ramo próprio `expense_parcela` antes do `else`.
- Lote (`financeiro_write.py:242-344`): um array de ids inteiros por tipo; o React faz `Number(i.id)`
  (`PagamentosPage.tsx:321`) e `_to_int` descarta o resto em silêncio. Decisão: `parcela_ids: number[]`, id da parcela
  inteiro — nunca id composto em texto.
- `StatusSelect` manda `valor_esperado = item.amount` só para `expense` (`PagamentoItemViews.tsx:139-143`): a parcela não
  manda, e a trava de valor da devolução não se aplica (devolução não parcela).

## R3. DRE e custo

`dre_ops.gastos_extras_do_periodo` usa `expense_date` e `amount` do aprovado (`dre_ops.py:24-43`); custo do evento,
comissões e marketing leem só `amount`. Com `amount` = soma, nada muda — é a decisão 1 do dono.

## R4. Reaproveitar parcelas existentes?

- `RecurringExpenseEntry` (feature 121): FK obrigatória para `recurring_expenses`, e a DRE e o auditor somam essas
  linhas como gasto recorrente — reaproveitar contaria o gasto em dobro. Rejeitado.
- `EventInstallment` (065): recebível da cliente, recriado inteiro a cada gravação (perderia a situação). Rejeitado.
- Precedente adotado: a linha com situação própria, como `RecurringExpenseEntry`, mas filha de `special_expenses`.

## R5. Quem reescreve o `amount` (quebraria a soma)

`cancel_ops` (devolução e multa: `:3324-3340`, `:2863-2870`) e o auditor de marketing (`desempenho_ops.py:747-749`).
Decisão: esses gastos não parcelam (400).

## R6. Status agregado

Nenhum status novo no gasto ("parcial" ficaria fora das somas de `totals` e do `bucketOf`). O `payment_status` do gasto
parcelado é derivado para um dos três valores existentes.
