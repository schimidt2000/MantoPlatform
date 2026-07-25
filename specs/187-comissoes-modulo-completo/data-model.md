# Data Model: Reestruturação do Módulo de Comissões

Nenhuma migração de schema. Entidade de banco já existente e reaproveitada como está:

## `CommissionPayment` (`commission_payments`, `app/models.py:738`)

| Campo | Tipo | Observação |
|---|---|---|
| `id` | `Integer` PK | |
| `event_id` | `Integer` FK → `calendar_events.id`, nullable | |
| `event_title` | `String(200)` | cópia — persiste mesmo se o evento for apagado |
| `seller_id` | `Integer` FK → `users.id`, not null | agrupador da visão "Resumo por Vendedor" |
| `sale_date` | `Date`, nullable | usado para filtrar por mês |
| `payable_from` | `Date`, nullable | ciclo especial EducaManto (fora de escopo desta feature) |
| `amount` | `Numeric(12,2)`, not null | positivo (comissão) ou negativo (estorno) |
| `status` | `String(20)` | `a_pagar` \| `pago` \| `cancelado` |
| `paid_at` | `Date`, nullable | setado no momento da liquidação |
| `notes` | `Text`, nullable | não usado por esta feature |
| `original_id` | `Integer` FK → `commission_payments.id`, nullable | referência do estorno ao registro original |

## Entidades derivadas (agregações em memória, não persistidas)

### `CommissionMonthSummaryRow` (uma linha por vendedor, visão "Resumo por Vendedor")

| Campo | Tipo | Origem |
|---|---|---|
| `seller_id` | int | `CommissionPayment.seller_id` |
| `seller_name` | str | `User.name` |
| `sale_count` | int | `COUNT(*)` de registros elegíveis do vendedor no mês |
| `total_amount` | Decimal | `SUM(amount)` (inclui estornos negativos) |
| `pending_amount` | Decimal | `SUM(amount) WHERE status='a_pagar'` — valor exato do botão "Pagar Mês" |
| `month_status` | `"pendente" \| "pago"` | `"pago"` somente se não há nenhum `a_pagar` elegível |
| `entries` | `CommissionEntry[]` | eventos individuais, para o accordion |

### `CommissionEntry` (uma linha por comissão, visão "Detalhamento de Vendas" e accordion)

Mesmo shape já serializado hoje por `_serialize_commission` em `financeiro_read.py:431`
(reaproveitado sem mudança): `id, seller_id, seller_name, event_id, event_title, sale_date,
amount, status, status_label, paid_at`.

### `CommissionKpis` (cards do topo)

| Campo | Tipo | Cálculo |
|---|---|---|
| `total_month` | Decimal | soma de todos os registros elegíveis do mês (`a_pagar` + `pago`, incluindo estornos) |
| `total_paid` | Decimal | soma de `status='pago'` |
| `total_pending` | Decimal | soma de `status='a_pagar'` (inclui estornos pendentes) |

### `PayoutResult` (retorno da liquidação em lote)

| Campo | Tipo | Descrição |
|---|---|---|
| `seller_id` | int | vendedor liquidado |
| `month` | str (`YYYY-MM`) | mês liquidado |
| `changed_count` | int | quantos registros passaram para `pago` nesta chamada (0 se nada elegível — ver Research §4) |
| `paid_total` | Decimal | soma do que foi liquidado nesta chamada |
| `summary` | `CommissionMonthSummaryRow` | estado atualizado do vendedor após a liquidação, para o frontend atualizar a linha sem novo GET |

## Regras de validação / transição de estado

- Um registro só é elegível para liquidação em lote se `status == 'a_pagar'` **e**
  `seller_id == alvo` **e** cai no mês solicitado (mesma regra de filtro de `sale_date`/
  `created_at` já usada em `api_financeiro_comissoes`).
- `status='cancelado'` nunca é elegível (não entra em nenhuma soma nem na liquidação).
- Transição válida por esta feature: `a_pagar → pago` (em lote). Não há transição inversa nesta
  tela (reverter pagamento continua sendo feito pela ação individual já existente, fora de
  escopo).
- RBAC de leitura: papel Comercial sem Financeiro/Superadmin → toda query (KPIs, resumo,
  detalhamento) filtra implicitamente `seller_id = current_user.id`, aplicado no servidor.
- RBAC de escrita: o endpoint de liquidação exige papel Financeiro ou Superadmin — reforçado no
  servidor independente do `seller_id` informado no corpo da requisição.
