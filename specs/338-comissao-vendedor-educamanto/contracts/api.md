# Contratos — Feature 338

## `PATCH /api/events/<id>/comercial` (alterado)

Gate de hoje: `_can_create_event()` (Comercial e Superadmin); satélite → 409; cancelado → só o
Superadmin real passa (`_recusa_se_cancelado`).

Campo novo no corpo, **opcional** (chave ausente = não mexe — o bundle antigo não apaga o valor):

```json
{ "educamanto_seller_commission": 1500.00 }
```

- `null`, `""` ou `0` → sem comissão do vendedor (grava `NULL`).
- Erros 400, envelope `json_error`, `fields.educamanto_seller_commission`:
  - valor não numérico ou negativo → "Informe um valor válido para a comissão do vendedor."
  - acima da venda, quando a venda tem valor → "A comissão do vendedor não pode passar do valor da venda."
    (venda "a definir" aceita o valor; a linha só nasce com a venda)
  - evento que não é EducaManto com responsável → "A comissão do vendedor só existe em evento EducaManto."
- Cortesia/permuta → grava `NULL` (a venda vai a zero).
- Evento cancelado com valor diferente do gravado → **409** `codigo: "cancelado"`, "A comissão do vendedor
  do evento cancelado é a do ato e não pode ser alterada." — para todos, o Superadmin inclusive.

Resposta: o detalhe do evento (`_event_detail_json`), como hoje.

## `GET /api/events/<id>` (detalhe — campos novos, todos opcionais no React)

- `venda.educamanto_seller_commission: number | null`
- `venda.mostra_comissao_do_vendedor: boolean` — evento EducaManto com responsável configurado.
- `kpi.commission` — **só a trilha principal** (a do responsável no EducaManto).
- `kpi.seller_commission: number | null` e `kpi.seller_commission_name: string | null` — a linha do
  vendedor (ou a estimativa, sem linha).

## `GET /api/financeiro/comissoes` e `GET /api/financeiro/pagamentos` (campos novos)

- `CommissionEntry.origem: "vendedor_educamanto" | null`
- `PagamentoItem.commission_lines[].origem: "vendedor_educamanto" | null`
- `CommissionMonthSummaryRow.sale_count` passa a contar eventos distintos com linha de comissão.

## DRE e Dashboard Comercial

Sem campo novo: `comissoes` (DRE) e `comissao_prevista` (Dashboard Comercial) passam a somar a comissão do
vendedor; `cancelamentos.comissao_retido` soma a do vendedor do retido.
