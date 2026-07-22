# Contrato: escrita da Planilha de Pagamentos (feature 160)

Gate em todas as rotas: usuário autenticado com papel FINANCEIRO ou SUPERADMIN
(`_has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN)`, mesma paridade da 159). Sem esse papel:
`403 {"error": {"message": "Sem permissão"}}`.

Envelope de sucesso/erro segue `specs/144-migracao-react-spa/contracts/api-conventions.md`, exceto
o endpoint de export (documentado à parte).

## `POST /api/financeiro/pagamentos/set-status`

- Body: `{"item_type": "cache"|"salary"|"expense"|"bv"|"commission"|"recurring", "item_id": number|string, "status": "nao_pago"|"pago"|"no_banco"}`
  - `item_id` de `commission` é `"sellerId:YYYY-MM"` (mesmo formato da serialização da 159).
- 200: `{"status": "<status efetivo aplicado>"}` — para `commission`, `"pago"` ou `"nao_pago"`
  (nunca `"no_banco"`, mesma regra de hoje).
- 400: `{"error": {"message": "Status inválido para este item"}}` — quando `status` não é válido
  para o `item_type`, ou o item não existe.

## `POST /api/financeiro/pagamentos/bulk-action`

- Body: `{"action": "pago"|"nao_pago"|"no_banco"|"delete", "role_ids": number[], "salary_ids": number[], "expense_ids": number[], "commission_ids": string[], "month": "YYYY-MM"}`
- 200: `{"changed": number, "skipped": string[]}` — `skipped` traz uma mensagem por grupo ignorado
  (ex.: `"2 gasto(s) — exclua pelo módulo de Gastos"`), mesmo texto das mensagens `flash` de hoje.
- Se nenhum id for enviado em nenhuma lista: `200 {"changed": 0, "skipped": []}` (sem efeito, sem
  erro).

## `POST /api/financeiro/pagamentos/salary/<int:sp_id>/advance`

- `Content-Type: multipart/form-data` (convenção da 153/155): campos `amount` (string BRL),
  `advance_date` (opcional, `YYYY-MM-DD`), arquivo `advance_proof` (obrigatório, ≤ 10 MB).
- 200: `{"id": number, "amount": number, "date": "YYYY-MM-DD", "proof": "/uploads/payments/..."}`
  (adiantamento criado).
- 400: `{"error": {"message": "..."}}` — valor ≤ 0, soma excede o salário, comprovante ausente, ou
  comprovante acima de 10 MB (mesmas 4 validações de `salary_advance` hoje).
- 404: lançamento de salário (`sp_id`) não encontrado.

## `POST /api/financeiro/pagamentos/salary/advance/<int:adv_id>/delete`

- Sem corpo.
- 204: adiantamento e comprovante removidos.
- 404: adiantamento não encontrado.

## `GET /api/financeiro/pagamentos/export?month=YYYY-MM`

- **Exceção ao envelope padrão** — resposta é `Content-Type: text/csv; charset=utf-8`,
  `Content-Disposition: attachment; filename=pagamentos_{month}.csv`, corpo é o CSV puro (mesmas
  colunas de `export_pagamentos()` hoje: Data, Evento, Função, Nome, Valor, Pix, Situação).
- `month` ausente/inválido cai no mês corrente, mesmo fallback da rota Jinja.
- Consumido pelo frontend via `apiFetchBlob` (não `apiFetch`) — ver `plan.md` Design Decision 6.
