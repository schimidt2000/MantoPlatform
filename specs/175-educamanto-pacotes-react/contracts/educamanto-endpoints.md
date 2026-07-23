# Contrato de API — EducaManto Pacotes/Conteúdos

Herda as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md`
(envelope de sucesso/erro, códigos HTTP). RBAC replicado por função, paridade com
`app/educamanto/routes.py` (`_CAN_USE`, `_CAN_PACKAGES`, `_CAN_MANAGE`).

## Leitura (`app/api/educamanto_read.py` — estendido)

### `GET /api/educamanto/packages` (já existe, sem mudança de shape)

- RBAC: `_CAN_USE` (COMERCIAL, SUPERADMIN, ENSAIO, REVENDEDOR_EDUCAMANTO)
- 200: `{"packages": [EducaMantoPackage.to_dict(), ...]}`

### `GET /api/educamanto/historico`

- RBAC: `_CAN_USE`
- Query params: `q`, `date_from`, `date_to` (todos opcionais); `user_id` só tem efeito para
  SuperAdmin (mesma regra do Jinja `historico()`)
- 200: `{"entries": [{"id", "created_at", "client_name", "packages_label", "user_name"}, ...], "users": [{"id","name"}, ...] }`
  — `users` só populado quando o requisitante é SuperAdmin (para o filtro "Gerado por");
  `user_name` só incluído por entrada quando SuperAdmin (mesma regra de exposição condicional já
  usada em outras fatias, ex. financeiro).

## Escrita (`app/api/educamanto_write.py` — novo)

### `POST /api/educamanto/packages`

- RBAC: `_CAN_MANAGE` (SUPERADMIN)
- Body: `{"name", "margin_1s", "margin_2s", "margin_1s_days", "margin_2s_days", "discount_days", "discount_pct", "commission_rate", "ensemble_1s", "ensemble_2s", "ensemble_1s_days", "ensemble_2s_days", "items": [{"name","qty","cost_1s","cost_2s","cost_1s_days","cost_2s_days","ensemble_add"}, ...]}`
- 201: `EducaMantoPackage.to_dict()`
- 400: erro de validação (`fields`) — ex. nome vazio, item sem nome

### `PATCH /api/educamanto/packages/<id>`

- RBAC: `_CAN_MANAGE`
- Body: mesmo shape do POST (substitui a lista de itens inteira — paridade com `edit_package`)
- 200: `EducaMantoPackage.to_dict()`
- 404: pacote não encontrado

### `POST /api/educamanto/packages/<id>/duplicate`

- RBAC: `_CAN_MANAGE`
- 201: `EducaMantoPackage.to_dict()` (cópia, nome prefixado "Cópia de ...")

### `DELETE /api/educamanto/packages/<id>`

- RBAC: `_CAN_MANAGE`
- 204
- 404: pacote não encontrado

### `POST /api/educamanto/orcamento/gerar`

- RBAC: `_CAN_USE`
- Body: mesmo shape hoje aceito por `POST /educamanto/orcamento/gerar` (Jinja) —
  `{"packages": [{"id","name","sem_nota","com_nota"}], "d1", "d2", "ensemble", "acrescimo", "transporte": {...}, "client_name"}`
- 200: PDF binário (`Content-Type: application/pdf`, `Content-Disposition: attachment`),
  consumido via `apiFetchBlob` — cria o registro de histórico como efeito colateral (paridade
  com `gerar_orcamento` legado)
- 400: `{"error": {"message": "Selecione ao menos um pacote."}}` ou "Preencha os dias..."

### `GET /api/educamanto/orcamento/<quote_id>/pdf`

- RBAC: `_CAN_USE`
- 200: PDF binário (`Content-Disposition: inline`), reconstituído a partir do `snapshot`
  congelado — nunca recalcula a partir do pacote atual
- 404: orçamento não encontrado

## Fora de escopo desta fatia

Qualquer endpoint do Portal do Artista (spec 176).
