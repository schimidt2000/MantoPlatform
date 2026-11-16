# Contratos — 344

Erro sempre no envelope `json_error` (`{"error": {"message", "fields"?}}`).

## `POST /api/virtuais/campanhas/<slug>/visita` — público, 30/min por IP
Corpo: `{"origem": "instagram"}` (qualquer texto; o servidor reduz). Resposta **204** sem corpo.
Campanha inexistente ou não publicada → **404**. Nunca grava IP.

## `GET /api/virtuais/rastreamento` — público
`{"meta_pixel_id": "123456789012345" | null}`

## `POST /api/virtuais/campanhas/<slug>/reservar` — inalterado + 3 campos opcionais
`buyer_name` (texto, ≤120), `marketing_opt_in` (bool), `origem` (texto; reduzido). Ausentes = como hoje.

## `GET /api/virtuais/campanhas/<id>/funil` — Comercial, Superadmin
```json
{
  "public_url": "https://alo.mantoproducoes.com.br/papai-noel",
  "links": [{"origem": "instagram", "rotulo": "Instagram", "url": ".../papai-noel?origem=instagram"}],
  "totais": {"visitas": 120, "reservas": 9, "vendas": 4, "conversao": 3.3},
  "por_origem": [{"origem": "instagram", "rotulo": "Instagram", "visitas": 80, "reservas": 6, "vendas": 3, "conversao": 3.8}],
  "por_dia": [{"dia": "2026-11-16", "visitas": 40, "reservas": 3, "vendas": 1}]
}
```
Reservas = pedidos criados (qualquer situação); vendas = pedidos com `paid_at` e não cancelados por
conflito. `por_dia` = últimos 14 dias, do mais antigo ao mais novo. Conversão = vendas ÷ visitas × 100
(1 casa; 0 quando não há visita). Sem papel → **403**.

## `GET /api/admin/settings` / `PATCH /api/admin/settings` — Superadmin (existentes)
Campo novo `meta_pixel_id`: só dígitos (até 20); vazio desliga; outra coisa → **400** no campo.

## `GET /api/clientes/<id>` (existente) — campos novos
`"marketing_opt_in_at": "2026-11-16T15:02:00" | null`, `"marketing_opt_in_source": "Loja: …" | null`,
`"source": "loja_virtual"`.

## `GET /api/clientes/metricas` (existente)
`new_by_month[].loja` (inteiro) ao lado de `formulario`, `kommo`, `manual`.
