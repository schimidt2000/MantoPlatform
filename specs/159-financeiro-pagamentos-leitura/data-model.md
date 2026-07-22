# Data Model: Planilha de Pagamentos em React (159)

Nenhuma tabela/campo novo — reaproveita entidades já existentes. Esta fatia só adiciona uma
serialização de leitura sobre a combinação de itens que já existia em `pagamentos()`
(`app/financeiro/routes.py:1088`).

## Entidades lidas (já existentes)

| Entidade                  | Uso na planilha de pagamentos                                              |
|---------------------------|------------------------------------------------------------------------------|
| `EventRole`                | cachês de talento do mês (`talent_id` preenchido, evento no mês)            |
| `SalaryPayment`             | salários (semanal/quinzenal) gerados para o mês, com `payment_status`      |
| `SalaryAdvance`             | adiantamentos de um `SalaryPayment` (valor, data, comprovante)             |
| `SpecialExpense`            | gastos aprovados com desembolso definido, não pagos na criação, no mês     |
| `EventAcrescimo`            | repasses de BV (`is_bv=True`) dos eventos do mês                           |
| `CommissionPayment`         | comissões do ciclo do mês anterior, agregadas por vendedor (dia 5 do mês)  |
| `RecurringExpenseEntry`     | contas recorrentes preenchidas (`a_pagar`/`pago`) do mês                   |

## Valores computados (reaproveitados de `app/financeiro/routes.py`, sem duplicar)

- `_resync_pending_commissions()` — roda antes de tudo, sem alterar o comportamento: gera
  comissões pendentes de sincronização, mesma regra das fatias 158/157.
- `_ensure_salary_payments(year, month)` — garante que os `SalaryPayment` do mês existem antes da
  consulta (cria os que faltam a partir do `SalaryHistory` vigente), preservando os já pagos e os
  com adiantamento lançado — mesma regra de hoje.
- `_pagamentos_query(month)` — `EventRole` com talento atribuído cujo evento cai no mês.
- `_build_payment_items(roles, salary_payments, today, expenses, now_dt)` — combina cachês,
  salários (líquido = bruto − soma de adiantamentos) e desembolsos de gastos aprovados numa lista
  única ordenada por data; marca `is_future` pelo horário de término do evento (cachês) ou pelo
  vencimento (salários/gastos).
- `_build_bv_items(bv_rows, today, now_dt)` — um item por repasse de BV; sinaliza `missing_data`
  quando não há chave PIX cadastrada para o recebedor.
- `_build_commission_items(period_start, period_end, due_date, today)` — uma linha por vendedor,
  somando as comissões `a_pagar`/`pago` cujo ciclo (`payable_from` ou `sale_date`) cai no mês
  anterior ao mês visualizado; datada no dia 5 do mês visto.
- `_build_recurring_items(year, month, today)` — um item por lançamento de conta recorrente com
  status `a_pagar`/`pago` no mês (lançamentos "registrado", sem valor, nunca entram).
- Totais do mês, todos somando `amount` dos itens combinados:
  - `total` = soma de todos os itens.
  - `pago` = soma dos itens com `status="pago"`.
  - `no_banco` = soma dos itens com `status="no_banco"`.
  - `pendente` = soma dos itens com `status="nao_pago"` e `is_future=False`.
  - `futuro` = soma dos itens com `status="nao_pago"` e `is_future=True`.
- `status_labels` = `_STATUS_LABELS` (`nao_pago`→"Não pago", `pago`→"Pago", `no_banco`→"No
  banco") — reaproveitado, não reimplementado no frontend.

## Serialização nova (só desta fatia)

- Cada item ganha um `type` (`cache`/`salary`/`bv`/`commission`/`recurring`), campos comuns
  (data ISO, favorecido, evento, valor `float`, PIX, status, `is_future`) e campos específicos:
  `gross_amount`/`advance_amount`/`advances` (lista de `{id, amount: float, date, proof}`,
  re-lida de `SalaryAdvance` — não da string BRL que `_build_payment_items` monta para o
  template Jinja) para `salary`; `missing_data` para `bv`.
