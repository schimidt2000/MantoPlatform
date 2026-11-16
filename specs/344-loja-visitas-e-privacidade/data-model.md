# Modelo de dados — 344

Migration `e344a1b2c3d4_loja_visitas_e_privacidade.py`, `down_revision = "f310b2a4c6e8"`, aditiva.

## Nova: `virtual_campaign_visits` (`VirtualCampaignVisit`)

| coluna | tipo | regra |
|---|---|---|
| id | Integer PK | |
| campaign_id | Integer FK `virtual_campaigns.id` ON DELETE CASCADE | NOT NULL |
| day | Date | NOT NULL — dia em São Paulo |
| origem | String(20) | NOT NULL — uma de `VIRTUAL_ORIGENS` |
| visits | Integer | NOT NULL, default 0 |

`UNIQUE(campaign_id, day, origem)` (`uq_virtual_visit_campaign_day_origem`) — é o alvo do upsert.

## `virtual_orders` (`VirtualOrder`) — colunas novas, todas nulas

| coluna | tipo | o quê |
|---|---|---|
| origem | String(20) | origem da visita que gerou o pedido |
| buyer_name | String(120) | "Seu nome" (de quem compra) |
| marketing_opt_in_at | DateTime | quando marcou a caixinha (nulo = não marcou) |
| marketing_opt_in_version | String(20) | versão do texto da caixinha (`VIRTUAL_ACEITE_VERSAO`) |

## `clients` (`Client`) — colunas novas, nulas

| coluna | tipo | o quê |
|---|---|---|
| marketing_opt_in_at | DateTime | último aceite de novidades |
| marketing_opt_in_source | String(160) | de onde veio ("Loja: Uma chamada com o Papai Noel") |

`source` ganha o valor `loja_virtual` (sem mudança de esquema; `client_metrics` ganha o balde `loja`).

## `site_settings` (`SiteSetting`) — coluna nova

| coluna | tipo | o quê |
|---|---|---|
| meta_pixel_id | String(30) | ID do Pixel da Meta; nulo/vazio = desligado |

## Constantes (`app/constants.py`)

- `VIRTUAL_ORIGENS = ("instagram", "facebook", "whatsapp", "google", "tiktok", "email", "outro", "direto")`
- `VIRTUAL_ACEITE_VERSAO = "2026-11-16"` — muda junto com o texto da caixinha.
- `VIRTUAL_DICAS_RETENCAO_DIAS = 30`
- `CLIENT_SOURCE_LOJA = "loja_virtual"`
