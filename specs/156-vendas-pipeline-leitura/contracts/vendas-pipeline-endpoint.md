# Contract: Pipeline de Vendas Endpoint (156)

Convenção geral: `specs/144-migracao-react-spa/contracts/api-conventions.md`.

## `GET /api/vendas/pipeline`

- **Auth**: sessão válida + (COMERCIAL/FINANCEIRO/SUPERADMIN ou responsável EducaManto
  configurado), senão 403 — paridade com `require_vendas`.
- **Requisição**: sem parâmetros.
- **200**:

```json
{
  "is_financeiro": false,
  "items": [
    {
      "event_id": 123,
      "title": "Show Exemplo",
      "group_label": null,
      "location": "Local X",
      "sale_date": "2027-05-01",
      "sale_value": 3000.0,
      "custo": 1200.0,
      "comissao": 75.0,
      "lucro": 1800.0,
      "with_invoice": true
    }
  ]
}
```

- `lucro` só aparece em cada item quando `is_financeiro` é `true` (Financeiro/Superadmin).
- `group_label` é `null` para evento normal; para evento principal de grupo, string com o nome
  do grupo (ex.: `"Turnê SP (3 eventos)"`).
- Eventos satélites não aparecem em `items` (consolidados no principal).
- **403**: usuário sem acesso a Vendas.
