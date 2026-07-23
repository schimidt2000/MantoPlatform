# Contrato de API: Gastos Extras (endpoints novos/alterados)

Segue o contrato geral já documentado em
`specs/144-migracao-react-spa/contracts/api-conventions.md` (envelope de erro
`{"error": {"message", "fields"?}}`, 400/401/403/404/500). Endpoints não listados aqui
(`POST /gastos`, `POST /gastos/<id>/aprovar`, `POST /gastos/<id>/rejeitar`,
`DELETE /gastos/<id>`, `GET /gastos/eventos`) mantêm a assinatura atual — só o RBAC interno
muda onde indicado.

## `GET /api/gastos` (alterado)

RBAC: qualquer usuário autenticado. Quando `is_financeiro(current_user)` (`FINANCEIRO` ou
`SUPERADMIN`): retorna todos os gastos + `totals`. Caso contrário: só os do próprio usuário
(igual hoje).

**Resposta 200**:
```json
{
  "expenses": [
    {
      "...": "campos atuais inalterados",
      "approved_with_edits": false
    }
  ],
  "can_manage": true,
  "categories": ["Figurino", "Escritório", "Marketing", "Manutenção", "Outros"],
  "totals": {
    "todos":     { "count": 12, "total": 4530.00 },
    "pendente":  { "count": 3,  "total": 890.00 },
    "aprovado":  { "count": 8,  "total": 3200.00 },
    "rejeitado": { "count": 1,  "total": 440.00 }
  }
}
```
`totals` só está presente quando `can_manage == true`. `can_manage` substitui o campo
`is_superadmin` de hoje (única mudança de nome — único consumidor é `GastosExtrasPage.tsx`).

## `PATCH /api/gastos/<id>` (novo)

RBAC: `is_financeiro(current_user)` (403 `json_error("Sem permissão", 403)` caso contrário).

**Body** (JSON):
```json
{
  "description": "Compra de tecido",
  "category": "Figurino",
  "amount": 512.30,
  "expense_date": "2026-07-20",
  "disbursement_type": "fornecedor",
  "supplier_name": "Tecidos ABC",
  "supplier_pix": "12.345.678/0001-90",
  "event_id": 42,
  "aprovar": true
}
```
- `disbursement_type`: `"reembolso" | "fornecedor" | ""` (vazio = sem desembolso definido).
- `reimburse_user_id` obrigatório se `disbursement_type == "reembolso"`.
- `supplier_name` obrigatório se `disbursement_type == "fornecedor"`.
- `event_id`: `null`/omitido remove o vínculo.
- `aprovar` (opcional, default `false`): se `true`, aprova o gasto na mesma operação.

**Respostas**:
- `200` — gasto atualizado (mesmo formato de `_expense_dict`, com `approved_with_edits`
  refletindo a regra de `data-model.md`).
- `400` — validação (`fields: {"description": "..."}`, etc., mesmo formato de `POST /gastos`).
- `403` — sem permissão (usuário não é `FINANCEIRO`/`SUPERADMIN`).
- `404` — gasto não encontrado.
- `409` — transição inválida (ex.: editar um `"rejeitado"` sem `aprovar: true`).

## Endpoints com RBAC alterado (mesma assinatura, novo critério de permissão)

| Endpoint | Antes | Depois |
|----------|-------|--------|
| `POST /gastos/<id>/aprovar` | `is_superadmin` | `is_financeiro` |
| `POST /gastos/<id>/rejeitar` | `is_superadmin` | `is_financeiro` |
| `POST /gastos/<id>/vincular-evento` | `is_superadmin` | `is_financeiro` |
| `DELETE /gastos/<id>` | `can_delete_expense` (superadmin sempre; dono+pendente) | `is_financeiro` sempre; dono+pendente (checagem nova só na API, não reusa `can_delete_expense`) |

A view Jinja legada (`app/gastos/routes.py`) **não muda** — continua com `is_superadmin` em
todos esses pontos, via as funções originais e intocadas de `gastos_ops.py`.
