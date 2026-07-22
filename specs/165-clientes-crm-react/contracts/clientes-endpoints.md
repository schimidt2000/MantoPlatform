# Contrato de API — Clientes (CRM) (165)

Segue as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md`
(envelope de sucesso/erro, códigos HTTP).

## `GET /api/clientes/search?q=`

- Gate: COMERCIAL/FINANCEIRO/SUPERADMIN (`require_vendas`).
- `q` com menos de 2 caracteres → `200 []`.
- 200: `[{"id", "name", "phone", "phone_display", "company"}, ...]` (até 10).

## `POST /api/clientes/quick-create`

- Gate: COMERCIAL/FINANCEIRO/SUPERADMIN.
- Body: `{"name": string, "phone": string, "phone_display"?: string, "email"?: string,
  "company"?: string}`.
- 200: `{"id", "name", "phone", "phone_display", "company", "reused": bool}`.
- 400: `{"error": {"message": "...", "fields": {"name"|"phone": "..."}}}`.

## `GET /api/clientes/`

- Gate: COMERCIAL/FINANCEIRO/SUPERADMIN.
- Querystring: `q` (opcional).
- 200: `{"items": [{"id", "name", "phone_display", "company", "event_count"}, ...],
  "total_clients": N}` (items já ordenados: nº eventos desc, nome asc; limite 300).

## `GET /api/clientes/<id>`

- Gate: COMERCIAL/FINANCEIRO/SUPERADMIN.
- 200: `{"id", "name", "phone", "phone_display", "email", "company", "cpf", "cnpj", "address",
  "events": [{"id", "title", "start_at", "relation"}, ...], "event_count", "total_sales": float}`.
- 404: cliente não encontrado.

## `PATCH /api/clientes/<id>`

- Gate: COMERCIAL/FINANCEIRO/SUPERADMIN.
- Body: `{"cpf"?: string, "cnpj"?: string, "address"?: string}` (campo ausente/vazio → `null`).
- 200: cliente atualizado (mesmo shape do detalhe, sem `events`/`total_sales`).

## `DELETE /api/clientes/<id>`

- Gate: SUPERADMIN/FINANCEIRO (mais restrito que os demais endpoints deste contrato).
- 204: cliente excluído, `EventClient` associados removidos, `client_id` dos eventos zerado.
- 403: usuário Comercial (sem Financeiro/Superadmin).
- 404: cliente não encontrado.

## `GET /api/clientes/avaliacoes`

- Gate: COMERCIAL/FINANCEIRO/SUPERADMIN.
- Querystring: `period` (`30d`/`90d`/`365d`/`custom`/`all`, default `all`), `from`/`to` (quando
  `custom`), `score` (`1`–`5`), `tag`, `client_id`.
- 200: `{"feedbacks": [{"id", "score", "tags": [...], "submitted_at", "event_title",
  "client_name"}, ...], "total", "avg_overall", "clients_rated", "dist": {"1".."5": N},
  "dist_max", "attention": [...mesma forma de feedbacks, até 10...],
  "clients_with_feedback": [{"id", "name"}, ...], "all_tags": [...tags conhecidas, para o
  seletor de filtro...], "filters": {"period", "from", "to", "score", "tag", "client_id"}}`.
