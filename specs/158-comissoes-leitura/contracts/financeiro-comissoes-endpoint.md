# Contract: Comissões Endpoint (158)

Convenção geral: `specs/144-migracao-react-spa/contracts/api-conventions.md`.

## `GET /api/financeiro/comissoes`

- **Auth**: sessão válida + (COMERCIAL/FINANCEIRO/SUPERADMIN, ou responsável EducaManto
  configurado independente de papel), senão 403 — paridade com `require_vendas` (reusa
  `_can_view_vendas`, já existente em `financeiro_read.py` desde a 156).
- **Query params** (opcional, mesmo default da view Jinja):
  - `month`: `YYYY-MM` (default: mês corrente; fallback para mês corrente se inválido)
- **200**:

```json
{
  "month": "2026-07",
  "can_manage": true,
  "total_a_pagar": 1240.0,
  "entries": [
    {
      "id": 501,
      "seller_id": 12,
      "seller_name": "Fulano",
      "event_id": 88,
      "event_title": "Show Exemplo",
      "sale_date": "2026-07-10",
      "amount": 375.0,
      "status": "a_pagar",
      "status_label": "A pagar",
      "paid_at": null
    }
  ],
  "estornos": [
    {
      "id": 480,
      "seller_id": 12,
      "seller_name": "Fulano",
      "event_id": 70,
      "event_title": "Evento Cancelado",
      "sale_date": "2026-06-02",
      "amount": -150.0,
      "status": "a_pagar",
      "status_label": "A pagar",
      "paid_at": null
    }
  ],
  "sellers": [
    { "id": 12, "name": "Fulano" }
  ]
}
```

- Todos os valores monetários são `number` (Decimal→float), nunca string formatada — mesma
  convenção da 156/157.
- `sellers` só aparece quando `can_manage=true` (Financeiro/Superadmin); quando `can_manage=false`,
  `entries`/`estornos` já vêm filtrados só do próprio `seller_id` do usuário autenticado.
- `403`: usuário sem papel Comercial/Financeiro/Superadmin e que não é o responsável EducaManto
  configurado.
