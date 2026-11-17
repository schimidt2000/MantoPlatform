# Modelo de dados — Feature 345

Migration única, **aditiva**, escrita à mão: `migrations/versions/f345c0a1b2d3_marketing_integrado.py`,
`down_revision = "e344a1b2c3d4"` (head da `main` em 16/11). Nenhuma coluna existente muda de tipo; nada é apagado.

## Colunas novas em tabelas existentes

### `catalog_items` (`CatalogItem`) — licença do tema

| coluna | tipo | default | regra |
|---|---|---|---|
| `licenca_origem` | String(16) NOT NULL | `'nao_classificado'` | `autoral` \| `licenciado` \| `nao_classificado` |
| `liberado_anuncio` | String(12) NOT NULL | `'nao_decidido'` | `sim` \| `nao` \| `nao_decidido` |
| `licenca_por_id` | Integer FK `users.id` SET NULL | null | quem marcou por último |
| `licenca_em` | DateTime (UTC) | null | quando |
| `licenca_sugestao` | String(16) | null | `autoral` \| `licenciado` (só a rotina escreve) |
| `licenca_sugestao_motivo` | Text | null | "personagem da Disney" |

- Só `liberado_anuncio == 'sim'` vai para anúncio (FR-010). `nao_decidido` vale como não.
- Confirmar origem `autoral` grava `liberado_anuncio='sim'`; confirmar `licenciado` grava `'nao'` (FR-009).
- `liberado_anuncio='sim'` num tema `licenciado` só por SUPERADMIN (FR-009b) — regra no `_ops`, não no endpoint.

### `marketing_posts` (`MarketingPost`) — o card vira pedido de criativo

| coluna | tipo | default | regra |
|---|---|---|---|
| `tipo` | String(10) NOT NULL | `'post'` | `post` \| `anuncio` |
| `frente` | String(16) | null | uma de `MARKETING_FRENTES` |
| `formato` | String(16) | null | `foto_1x1` \| `foto_4x5` \| `foto_9x16` \| `video_9x16` \| `video_1x1` |
| `briefing_objetivo` | Text | null | |
| `briefing_mostrar` | Text | null | |
| `briefing_letreiro` | Text | null | |
| `origem` | String(10) NOT NULL | `'pessoa'` | `pessoa` \| `rotina` |

- Card `tipo='anuncio'` só aceita temas com `liberado_anuncio='sim'` (422 `tema_nao_liberado`).
- Card antigo continua `tipo='post'`, `origem='pessoa'`: nada muda para o que existe (Princípio IV).

### `marketing_campaign_metrics` — conversas e cadastros por campanha

| coluna | tipo | regra |
|---|---|---|
| `conversations` | Integer null | conversas iniciadas (Meta: `messaging_conversation_started_7d`) |
| `leads` | Integer null | cadastros (formulário / contato) |

Entram em `_CAMPAIGN_INT_COLS` da 256 — o `POST /run` passa a aceitá-las sem outra mudança.

### `site_settings` (`SiteSetting`, singleton `id=1`)

| coluna | tipo | regra |
|---|---|---|
| `marketing_resp_foto_id` | Integer FK `users.id` SET NULL | responsável por pedido de foto/arte |
| `marketing_resp_video_id` | Integer FK `users.id` SET NULL | responsável por pedido de vídeo |

## Tabelas novas

### `marketing_frentes` — teto por frente

`slug` String(16) PK (`corporativo`, `social`, `educamanto`, `festas`, `loja`) · `teto_custo_venda` Numeric(12,2) null
(null = usa o padrão calculado) · `updated_by_id` FK users SET NULL · `updated_at` DateTime.
A migration semeia as 5 linhas com teto null.

### `marketing_campanha_frentes` — correção manual da frente

`id` · `platform` String(20) · `campaign_id` String(80) · `frente` String(16) · `updated_by_id` · `updated_at`.
`UNIQUE(platform, campaign_id)`. Vence o prefixo do nome (FR-002).

### `marketing_ad_metrics` — desempenho por anúncio e dia

`id` · `platform` String(20) · `ad_id` String(80) · `ad_name` String(300) · `adset_id` String(80) ·
`campaign_id` String(80) · `campaign_name` String(200) · `metric_date` Date · `spend` Numeric(12,2) ·
`currency` String(3) default BRL · `impressions`, `reach`, `clicks`, `conversations`, `leads`, `results` Integer null ·
`updated_at` DateTime. `UNIQUE(platform, ad_id, metric_date)` — upsert idempotente (FR-001). Índice em
`(platform, campaign_id, metric_date)`.

### `marketing_post_anuncios` — card ↔ anúncio

`id` · `post_id` FK `marketing_posts.id` CASCADE · `platform` String(20) · `ad_id` String(80) · `created_at`.
`UNIQUE(platform, ad_id)`: um anúncio pertence a um card só.

### `marketing_propostas`

| coluna | tipo | regra |
|---|---|---|
| `id` | PK | |
| `tipo` | String(12) | `ativar` \| `pausar` \| `verba` \| `publico` |
| `platform` | String(20) | `Meta Ads` \| `Google Ads` |
| `alvo_tipo` | String(10) | `campanha` \| `conjunto` \| `anuncio` |
| `alvo_id`, `alvo_nome` | String(80) / String(300) | |
| `valor_antes`, `valor_depois` | String(200) null | texto livre ("R$ 30/dia" → "R$ 45/dia") |
| `custo_dia_estimado` | Numeric(12,2) null | |
| `motivo`, `evidencia` | Text | obrigatório `motivo` |
| `post_id` | FK `marketing_posts.id` SET NULL | card de onde saiu (ativar anúncio) |
| `situacao` | String(10) NOT NULL default `pendente` | `pendente` → `aprovada` \| `recusada` \| `expirada`; `aprovada` → `executada` \| `falhou` |
| `criada_em` | DateTime (UTC) | |
| `decidida_por_id`, `decidida_em`, `decisao_obs` | | só SUPERADMIN decide (FR-016) |
| `executada_em`, `resultado_execucao` | | só o agente escreve |

- Expiração preguiçosa: toda leitura/decisão roda `UPDATE … SET situacao='expirada' WHERE situacao='pendente' AND
  criada_em < agora − 7 dias` antes de decidir (FR-018).
- Decisão com `SELECT … FOR UPDATE` e releitura (`docs/00` §6 item 26): quem chega em proposta não pendente leva 409
  `ja_decidida`.
- Proposta `ativar` com `post_id` cujo card tem tema não liberado → 422 na criação (FR-010).

### `marketing_diario`

`id` · `titulo` String(200) · `motivo` Text · `evidencia` Text null · `resultado_esperado` Text null ·
`reavaliar_em` Date (padrão: hoje SP + 14) · `resultado_observado` Text null · `veredito` String(14) null
(`funcionou` \| `nao_funcionou` \| `inconclusivo`) · `avaliado_em` DateTime null · `origem` String(10)
(`proposta` \| `pessoa` \| `rotina`) · `proposta_id` FK SET NULL **UNIQUE** (uma entrada por proposta) ·
`autor_id` FK SET NULL · `criado_em` DateTime.

- "A reavaliar": `reavaliar_em <= hoje (SP)` e `avaliado_em IS NULL`.

## Regras derivadas (sem coluna)

- **Frente da campanha**: correção manual > prefixo do nome (`CORP`, `SOCIAL`, `EDU`, `FESTA`, `LOJA`, primeira
  palavra, sem diferenciar maiúsculas) > `None` ("sem frente").
- **Frente da venda**: `(EDU` no título ou tipo `EDUCAMANTO` → educamanto; tipo `CORP` → corporativo; regex
  `15 anos|debut|casamento|noiv|bodas` no título → social; tipo `VM`/`VIRTUAL` → loja; resto → festas.
- **Venda do período**: `sale_date` na janela, `sale_value > 0`, `cancelled_at IS NULL`, `is_cortesia_permuta` falso,
  `group_leader_id IS NULL`.
- **Cliente novo**: `client_id` preenchido e nenhum outro evento não cancelado do mesmo cliente com `start_at` anterior.
- **Teto padrão**: 25% da mediana de (venda − cachês não dispensados − gastos extras aprovados do evento) das vendas da
  frente nos últimos 365 dias; sem venda, sem teto.
