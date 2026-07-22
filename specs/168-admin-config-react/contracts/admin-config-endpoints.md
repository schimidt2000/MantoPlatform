# Contrato de API — Configurações/Logs/Sync/Desempenho/Migração (168)

Todos os endpoints: gate SUPERADMIN.

## `GET /api/admin/settings`

200: todos os campos de `SiteSetting` (mesmos nomes do modelo, `logo_path` vira `logo_url` via
`assetUrl`-compatível).

## `PATCH /api/admin/settings` (multipart quando há `logo`)

Body: mesmos campos do form antigo (`default_commission_rate`, `educamanto_seller_id`,
`tax_rate`, `fator_r_threshold`, `manto_address`, `departure_margin_minutes`,
`google_maps_api_key`, `email_notifications_enabled`, `whatsapp_form_number`, `release_date`,
`logo`? arquivo). 200: settings atualizado.

## `GET /api/admin/logs`

Querystring: `entity_type`?, `actor`?, `page` (default 1). 200: `{"items": [...], "page",
"pages", "total", "entity_types": [...]}`.

## `GET /api/admin/desempenho`

Querystring: `month` (`YYYY-MM`). 200: `{"month", "casting": [{"name","count"}, ...],
"figurino": [...], "vendas": [{"name","count","total"}, ...], "totals": {...}}`.

## `GET /api/admin/sync-status`

200: `{"months": [{"ym","age_min","fresh","count"}, ...], "auto_sync_age_min", "recent_logs":
[...]}`.

## `POST /api/admin/sync/run`

Body: `{"action": "sync_now"|"cleanup_past"}`. 200: `{"results": [{"ym","ok","count"|"removed",
"err"?}, ...], "message"}`.

## `POST /api/admin/portal-announcement`

200: `{"sent", "failed"}`.

## `GET /api/admin/migrar-arquivos/status`

200: `{"pending_count", "pending": [...], "status": {...migration_status}}`.

## `POST /api/admin/migrar-arquivos/start`

200: `{"started": bool}` (`false` com mensagem amigável se já em andamento).

## `GET /api/admin/importar-catalogo/status`

200: `{"total_items", "status": {...import_status}}`.

## `POST /api/admin/importar-catalogo/start`

200: `{"started": bool}`.
