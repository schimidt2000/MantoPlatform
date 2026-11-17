# Modelo de dados — 348 Origem completa

Migration à mão `a348c0d1e2f3_origem_completa.py`, `down_revision = "d334b2c4e6f8"`, aditiva. Relógio: todo carimbo
novo é **UTC naive** (`agora_utc()`), como o resto das tabelas do CRM.

## Tabela nova: `origem_codigos` (`OrigemCodigo`)

Um clique de campanha que chegou ao site. Nasce pelo `POST /api/origem/codigo`; liga uma conversa só.

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `codigo` | String(8) NOT NULL UNIQUE | 5 caracteres do alfabeto sem ambíguos, maiúsculos |
| `gclid`, `gbraid`, `wbraid`, `fbclid` | String(512) | o que veio na URL, cortado |
| `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` | String(200) | idem |
| `campanha_id` | String(80) | `gad_campaignid` ou, na falta, `utm_id` |
| `pagina` | String(500) | caminho da página de entrada, sem a query |
| `procedencia` | String(200) | só o host do `document.referrer` externo |
| `created_at` | DateTime NOT NULL | UTC; vale por 90 dias (`K.VALIDADE_DO_CODIGO`) |
| `conversa_id` | FK `conversas.id` ON DELETE SET NULL, index | o primeiro uso; `UPDATE … WHERE conversa_id IS NULL` |
| `usado_em` | DateTime | UTC do momento da mensagem que o trouxe |
| `form_response_id` | FK `form_responses.id` ON DELETE SET NULL | a resposta de formulário enviada com o código |

Regras: sem nenhum marcador (`gclid`, `gbraid`, `wbraid`, `fbclid`, `campanha_id`, `utm_*`) o código não nasce.

## `conversa_anuncios` (`ConversaAnuncio`, 334) — contato de origem da conversa

| Coluna nova | Tipo | Regra |
|---|---|---|
| `ctwa_clid` | String(512) | do `referral` do WhatsApp; retroativo na migration |
| `codigo_id` | FK `origem_codigos.id` ON DELETE SET NULL | só no tipo `site` |

Tipo novo: `site` (`K.CONTATO_SITE`). Chave do contato pelo site: `site:{codigo}` (UNIQUE da 334 segura o reenvio).
`titulo` = `utm_campaign` (ou "Google"/"Site"); `link` = `pagina`; `anuncio_id` nulo.

## `anuncios_meta` (`AnuncioMeta`, 334)

| Coluna nova | Tipo |
|---|---|
| `conjunto_id` | String(64) |
| `conjunto_nome` | String(255) |

Dado: `UPDATE anuncios_meta SET consultado_em = NULL WHERE erro IS NULL AND NOT definitivo AND consultado_em IS NOT
NULL` — volta à fila uma vez para ganhar o conjunto.

## `orcamento_history` (`OrcamentoHistory`)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `conversa_id` | FK `conversas.id` ON DELETE SET NULL, index | primeiro envio pela conversa; `UPDATE … WHERE conversa_id IS NULL` |
| `origem_contato_id` | FK `conversa_anuncios.id` ON DELETE SET NULL | congelado junto, regra R7 |

## `calendar_events` (`CalendarEvent`)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `conversa_id` | FK `conversas.id` ON DELETE SET NULL, index | do orçamento (R8) ou da criação (`conversa_id`) |
| `origem_contato_id` | FK `conversa_anuncios.id` ON DELETE SET NULL | congelado, regra R7 |
| `frente` | String(16), FK `marketing_frentes.slug` | escolhida na aba Comercial; nula = ninguém escolheu |

As três são dados da venda: valem no principal; o satélite é lido pelo principal (`frente_do_evento`,
`origem_da_venda`). Não entram em `SATELLITE_FIELDS_CLEARED` (nada a apagar: o satélite não as recebe por tela).

## `clients` (`Client`)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `utm_campaign_id` | String(80) | id da campanha de origem: do anúncio da Meta (consulta) ou do código do site |

Dado: `UPDATE clients SET utm_campaign_id = anuncios_meta.campanha_id FROM anuncios_meta WHERE
clients.anuncio_origem_id = anuncios_meta.anuncio_id AND clients.utm_source = 'meta' AND clients.utm_medium = 'anuncio'
AND clients.utm_campaign_id IS NULL AND anuncios_meta.campanha_id IS NOT NULL`.

## Diagrama das ligações

```text
origem_codigos ──(codigo_id)──┐
                              ▼
conversas ◄──(conversa_id)── conversa_anuncios ◄──(origem_contato_id)── orcamento_history
    ▲                                    ▲                                     │ (orcamento_history_id)
    │                                    └──(origem_contato_id)── calendar_events ◄┘
    └────────────(conversa_id)────────── orcamento_history / calendar_events
calendar_events.frente ──► marketing_frentes.slug
```

## Downgrade

Remove as colunas, a FK da frente e a tabela `origem_codigos` (na ordem inversa). O `ctwa_clid` retroativo e o
`utm_campaign_id` saem junto com as colunas.
