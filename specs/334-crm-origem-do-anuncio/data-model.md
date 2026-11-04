# Modelo de dados — 334

Migration `d334b2c4e6f8` (`down_revision = "c333e1a5b7d9"`), aditiva.

## `conversa_anuncios` (nova)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `conversa_id` | Integer, FK `conversas.id` `ON DELETE CASCADE`, índice | |
| `canal` | String(20) | `whatsapp` ou `instagram`. |
| `chave` | String(255), UNIQUE (`uq_conversa_anuncios_chave`) | O wamid/mid da mensagem; no Instagram sem mensagem, `ref:{igsid}:{timestamp}`. |
| `tipo` | String(20) | `anuncio`, `publicacao` ou `outro`. Só `anuncio` é consultado e atribuído. |
| `anuncio_id` | String(64), nullable, índice | O id do anúncio (ou da publicação). |
| `titulo` | String(255), nullable | `headline` / `ad_title`. |
| `link` | Text, nullable | `source_url` (WhatsApp). |
| `momento` | DateTime | UTC: quando a cliente clicou (o timestamp do aviso). |
| `created_at` | DateTime | UTC. |

## `anuncios_meta` (nova)

| Coluna | Tipo | Regra |
|---|---|---|
| `anuncio_id` | String(64) PK | |
| `nome` | String(255), nullable | O nome do anúncio na Meta. |
| `campanha_id` | String(64), nullable | |
| `campanha_nome` | String(255), nullable | É o nome que o Desempenho casa com o export de campanhas. |
| `consultado_em` | DateTime, nullable | UTC da última consulta (com sucesso ou não). |
| `erro` | String(255), nullable | O motivo da última falha. |
| `definitivo` | Boolean, NOT NULL, `server_default false` | 404/não existe: não tenta de novo. |

## `clients` (existe)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `anuncio_origem_id` | String(64), nullable | O primeiro anúncio; nunca sobrescrito. |
| `anuncio_origem_em` | DateTime, nullable | UTC. |
| `anuncio_recente_id` | String(64), nullable | O anúncio mais recente. |
| `anuncio_recente_em` | DateTime, nullable | UTC. |

`lead_origin` ganha os valores "Anúncio do WhatsApp", "Anúncio do Instagram", "WhatsApp" e "Instagram". `utm_source`
ganha `meta` e `utm_medium` ganha `anuncio`; `utm_campaign` recebe o nome da campanha do primeiro anúncio.
