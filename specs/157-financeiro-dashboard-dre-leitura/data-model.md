# Data Model: Dashboard Financeiro (DRE) em React (157)

Nenhuma tabela/campo novo — reaproveita entidades já existentes. Esta fatia só adiciona uma
serialização de leitura sobre agregações que já existiam em `dashboard()`
(`app/financeiro/routes.py:387`).

## Entidades lidas (já existentes)

| Entidade                | Uso no dashboard                                                          |
|--------------------------|----------------------------------------------------------------------------|
| `CalendarEvent`          | eventos do período (DRE, KPIs, tabela, receita por tipo, top vendedores)   |
| `EventRole`              | cachês de talento (`_group_cost`/`_event_cost`, pagamentos pendentes/realizados) |
| `EventPayment`           | comprovantes de recebimento (`a_receber_clientes`)                          |
| `EventInstallment`       | parcelas a vencer no período, ainda não recebidas (`recebimentos_previstos`) |
| `EventInvoice`           | notas fiscais a emitir (todas) e custo de nota emitida no período           |
| `SpecialExpense`         | gastos extras aprovados no período (`gastos_extras`)                        |
| `RecurringExpenseEntry`  | lançamentos recorrentes do período, exceto `pulado` (`gastos_recorrentes`)  |
| `SalaryHistory`          | salário vigente por usuário, para pro-rata (`_salary_cost`)                 |
| `SalaryPayment`          | pagamentos de salário já gerados no mês (`_salary_cost`, mês cheio)         |
| `SiteSetting`            | `tax_rate`, `fator_r_threshold`, `default_commission_rate`                  |
| `User`                   | top vendedores (nome do usuário por `seller_id`)                           |

## Valores computados (reaproveitados de `app/financeiro/routes.py`, sem duplicar)

- `dre.{realizado,projetado,total}` = `_compute_drg(events_subset, settings, salary_cost,
  gastos_extras, gastos_recorrentes)` — chamado 3x com subconjuntos diferentes de eventos (mesma
  regra hoje: projetado usa custo fixo zerado).
- `kpis.ticket_medio` = receita bruta do total ÷ nº de eventos com venda (não-permuta, não-satélite).
- `kpis.ratio_custo_talento` = `_pct(cpv, receita_liquida)` do DRE total.
- `kpis.breakeven_pct`/`breakeven_atingido` = `_pct(lucro_bruto, custo_fixo)` onde custo_fixo =
  pessoal + comissões (DRE total).
- `kpis.fator_r_pct`/`fator_r_protegido` = `_pct(pessoal, receita_bruta)` vs.
  `_get_fator_r_threshold(settings)`.
- `paineis.receita_por_tipo` = soma de `sale_value` por `event_type`, eventos com venda.
- `paineis.top_sellers` = top 5 `seller_id` por receita, com lucro (receita − `_group_cost`).
- `paineis.monthly_trend` = últimos 6 meses (`_month_range`/`_prev_month`), receita/custo/lucro/
  margem/nº eventos.
- `paineis.auditoria` = eventos sem permuta/satélite com `sale_value` vazio ou ≤ 0.
- `eventos[]` = por evento do período (exceto satélite): `custo` (`_group_cost`/`_event_cost`),
  `comissao` (`_event_commission`), `rate` (`_get_commission_rate`), `status` financeiro
  (permuta/sem_valor/pago_total/parcial/pendente conforme recebido vs. venda).
- `pendencias.recebimentos_previstos` = `EventInstallment` com `due_date` no período e
  `received=False`.
- `pendencias.nf_a_emitir` = `EventInvoice` com `status='a_emitir'` (todas, sem filtro de período).
- `pendencias.custo_nota_itens` = `EventInvoice` com `issue_date` no período, custo =
  `amount * tax_rate / 100`.
