# Data Model: Comissões em React (158)

Nenhuma tabela/campo novo — reaproveita entidades já existentes. Esta fatia só adiciona uma
serialização de leitura sobre a query que já existia em `comissoes()`
(`app/financeiro/routes.py:1568`).

## Entidades lidas (já existentes)

| Entidade            | Uso na tela de comissões                                                        |
|---------------------|----------------------------------------------------------------------------------|
| `CommissionPayment`  | linhas do mês (`status` a_pagar/pago) e estornos pendentes (`status=a_pagar`, `amount<0`) |
| `User`               | nome do vendedor (`seller_id`); lista de vendedores elegíveis (papel Comercial)  |
| `Role`               | filtro de vendedores elegíveis (papel `COMERCIAL`)                               |
| `SiteSetting`        | `educamanto_seller_id` (exceção de acesso do responsável EducaManto)             |

## Valores computados (reaproveitados de `app/financeiro/routes.py`, sem duplicar)

- `_resync_pending_commissions()` — roda antes da query, sem alterar o comportamento: gera
  comissões pendentes de sincronização (eventos realizados sem linha ainda) e comissões
  EducaManto liberadas (após `payable_from`).
- `entries` = `CommissionPayment` com `status IN (a_pagar, pago)` cujo `sale_date` cai no mês
  filtrado, ou (quando `sale_date IS NULL`) cuja `created_at` cai no mês — ordenado por
  `sale_date ASC, seller_id ASC`, mesma query de hoje.
- `estornos` = `CommissionPayment` com `status=a_pagar` e `amount<0` (não filtrado por mês) —
  ordenado por `created_at ASC`.
- `can_manage` = `_has_role(FINANCEIRO, SUPERADMIN)`; quando falso, ambas as queries acima são
  restritas a `seller_id=current_user.id` — mesma regra de hoje.
- `total_a_pagar` = soma de `amount` das `entries` com `status=a_pagar` + soma de `amount` dos
  `estornos` — mesmo cálculo de hoje.
- `sellers` = `User` com papel `COMERCIAL`, ordenado por nome — só incluído quando `can_manage`.
- `status_labels` = `_COMMISSION_STATUS_LABELS` (`a_pagar`→"A pagar", `pago`→"Pago",
  `cancelado`→"Cancelado") — reaproveitado, não reimplementado no frontend.
