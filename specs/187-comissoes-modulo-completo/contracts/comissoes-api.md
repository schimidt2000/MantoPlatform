# Contrato de API — Módulo de Comissões (feature 187)

Segue as convenções gerais em `specs/144-migracao-react-spa/contracts/api-conventions.md`
(envelope de erro `{"error": {"message", "fields"?}}`, status 400/401/403/404/500).

## `GET /api/financeiro/comissoes`

Endpoint já existente (`app/api/financeiro_read.py`), payload evoluído nesta feature.

**Query params**:
- `month` (`YYYY-MM`, default: mês corrente)
- `seller_id` (int, opcional — só tem efeito se `can_manage=true`; ignorado/forçado ao próprio
  usuário quando `can_manage=false`)

**200** (usuário Comercial, `can_manage=false`):

```json
{
  "month": "2026-07",
  "can_manage": false,
  "title": "Minhas Comissões",
  "kpis": { "total_month": 4200.00, "total_paid": 1800.00, "total_pending": 2400.00 },
  "by_seller": [
    {
      "seller_id": 12,
      "seller_name": "Ana Souza",
      "sale_count": 3,
      "total_amount": 4200.00,
      "pending_amount": 2400.00,
      "month_status": "pendente",
      "entries": [ { "id": 501, "seller_id": 12, "seller_name": "Ana Souza", "event_id": 88, "event_title": "Show X", "sale_date": "2026-07-05", "amount": 1200.00, "status": "a_pagar", "status_label": "A pagar", "paid_at": null } ]
    }
  ],
  "entries": [ /* mesmo shape de CommissionEntry, uma linha por comissão — visão "Detalhamento de Vendas" */ ]
}
```

**200** (Financeiro/Superadmin, `can_manage=true`): mesmo shape, mais `title: "Comissões"`,
`sellers: [{ "id", "name" }]` (para o filtro rápido) e `by_seller`/`entries` cobrindo todos os
vendedores (ou só o filtrado, se `seller_id` for passado).

**403**: usuário sem nenhum papel de vendas (`_can_view_vendas` retorna falso) —
`{"error": {"message": "Sem permissão"}}`.

## `POST /api/financeiro/comissoes/pagar-mes` (NOVO)

Liquidação em lote atômica de um vendedor em um mês.

**Auth**: exige papel Financeiro ou Superadmin (`_require_financeiro()`). Vendedor comum
recebe 403 mesmo tentando liquidar o próprio `seller_id`.

**Body**:

```json
{ "seller_id": 12, "month": "2026-07" }
```

**200** — sucesso (inclusive quando não havia mais nada elegível — idempotente):

```json
{
  "seller_id": 12,
  "month": "2026-07",
  "changed_count": 2,
  "paid_total": 2400.00,
  "summary": {
    "seller_id": 12,
    "seller_name": "Ana Souza",
    "sale_count": 3,
    "total_amount": 4200.00,
    "pending_amount": 0.00,
    "month_status": "pago",
    "entries": [ "..." ]
  }
}
```

**400**: `seller_id` ausente/inválido ou `month` fora do formato `YYYY-MM` —
`{"error": {"message": "Mês inválido", "fields": {"month": "Use o formato AAAA-MM"}}}`.

**403**: usuário autenticado sem papel Financeiro/Superadmin —
`{"error": {"message": "Sem permissão"}}`.

**404**: `seller_id` não corresponde a nenhum usuário com papel Comercial —
`{"error": {"message": "Vendedor não encontrado"}}`.

Nota: **não** há erro específico para "nada elegível" — retorna 200 com `changed_count: 0` e o
`summary` atualizado (idempotência, ver `data-model.md` e `research.md` §4). O frontend usa
`changed_count` só para a mensagem de feedback (toast), não para decidir sucesso/erro.
