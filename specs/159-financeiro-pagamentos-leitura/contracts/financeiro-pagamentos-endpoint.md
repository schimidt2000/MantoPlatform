# Contract: Pagamentos Endpoint (159)

Convenção geral: `specs/144-migracao-react-spa/contracts/api-conventions.md`.

## `GET /api/financeiro/pagamentos`

- **Auth**: sessão válida + papel FINANCEIRO ou SUPERADMIN, senão 403 — paridade com
  `require_financeiro` (`_has_role(FINANCEIRO, SUPERADMIN)`, sem exceção de responsável
  EducaManto e sem recorte por vendedor, diferente de comissões/pipeline).
- **Query params** (opcional, mesmo default da view Jinja):
  - `month`: `YYYY-MM` (default: mês corrente; fallback para mês corrente se inválido)
- **200**:

```json
{
  "month": "2026-07",
  "totals": {
    "total": 18420.5,
    "pago": 9200.0,
    "no_banco": 1500.0,
    "pendente": 4320.5,
    "futuro": 3400.0
  },
  "status_labels": {
    "nao_pago": "Não pago",
    "pago": "Pago",
    "no_banco": "No banco"
  },
  "items": [
    {
      "type": "cache",
      "id": 501,
      "date": "2026-07-10",
      "event_title": "Show Exemplo",
      "event_id": 88,
      "copy_label": "10/07/2026 - Show Exemplo",
      "sublabel": "Personagem X",
      "person_name": "Fulano de Tal",
      "amount": 800.0,
      "pix_key": "fulano@pix.com",
      "pix_key_type": "email",
      "status": "nao_pago",
      "is_future": false
    },
    {
      "type": "salary",
      "id": 77,
      "date": "2026-07-06",
      "event_title": "Salário",
      "event_id": null,
      "copy_label": "06/07/2026 - Salário Ciclana",
      "sublabel": "semanal",
      "person_name": "Ciclana",
      "amount": 1450.0,
      "gross_amount": 1500.0,
      "advance_amount": 50.0,
      "advances": [
        { "id": 12, "amount": 50.0, "date": "2026-07-02", "proof": "" }
      ],
      "pix_key": "12345678900",
      "pix_key_type": "cpf",
      "status": "pago",
      "is_future": false
    },
    {
      "type": "bv",
      "id": 340,
      "date": "2026-07-15",
      "event_title": "Evento Corporativo",
      "event_id": 90,
      "copy_label": "15/07/2026 - Evento Corporativo",
      "sublabel": "BV (repasse)",
      "person_name": "(sem recebedor)",
      "amount": 200.0,
      "pix_key": "",
      "pix_key_type": "",
      "status": "nao_pago",
      "is_future": true,
      "missing_data": true
    },
    {
      "type": "commission",
      "id": "12:2026-06",
      "date": "2026-07-05",
      "event_title": "Comissões 06/2026",
      "event_id": null,
      "copy_label": "05/07/2026 - Comissão Fulano",
      "sublabel": "Comissão",
      "person_name": "Fulano",
      "amount": 375.0,
      "pix_key": "fulano@pix.com",
      "pix_key_type": "email",
      "status": "nao_pago",
      "is_future": false
    },
    {
      "type": "recurring",
      "id": 19,
      "date": "2026-07-10",
      "event_title": "Aluguel",
      "event_id": null,
      "copy_label": "10/07/2026 - Aluguel",
      "sublabel": "Conta recorrente",
      "person_name": "Aluguel",
      "amount": 3200.0,
      "pix_key": "",
      "pix_key_type": "",
      "status": "nao_pago",
      "is_future": false
    }
  ]
}
```

- Todos os valores monetários são `number` (Decimal→float), nunca string formatada — inclusive os
  itens de `advances`, diferente da lista que `_build_payment_items` monta hoje para o template
  Jinja (lá, `amount` já vem formatado em BRL como string).
- `403`: usuário sem papel Financeiro/Superadmin.
