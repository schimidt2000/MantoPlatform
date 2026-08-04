# Data Model — Loja de Interações Virtuais (feature 205)

**Data**: 2026-07-30 | **Spec**: [spec.md](./spec.md) | **Pesquisa**: [research.md](./research.md)

Seis tabelas novas, uma constante nova de tipo de evento e nenhuma alteração destrutiva no schema
existente. Migration manual em Alembic (Princípio: migrations sempre à mão), `down_revision` =
`b7d4f81a6e0c` (head atual, `migrations/versions/b7d4f81a6e0c_marketing_multiplos_temas.py`).

## Reaproveitamento (o que NÃO criamos)

| Precisa de | Usa o que já existe | Onde |
|---|---|---|
| Personagem vendável | `CatalogCharacter` | `app/models.py:1858` |
| Figurino do personagem | `CatalogCharacter.figurino_sheet_id` → `FigurinoSheet` | `app/models.py:1878` |
| Peça 3D do presente | `Acervo3DItem` | `app/models.py:1891` |
| Pendência de impressão | `Event3DGift` (status `pendente`) | `app/models.py:1942` |
| Evento operacional | `CalendarEvent` | `app/models.py:206` |
| Escala do talento | `EventRole` | `app/models.py:447` |
| Configuração/segredos | `SiteSetting` | `app/models.py:680` |
| Upload de arquivo | `app/storage.py` `save_file`/`delete_file` | — |
| Auditoria | `app.utils.audit` | — |

---

## Constantes novas (`app/constants.py`)

```python
EVENT_TYPE_VIRTUAL = "VIRTUAL"          # canal "loja virtual" — segrega KPIs e comissão (FR-052/054)

VIRTUAL_MODALITY_AO_VIVO  = "ao_vivo"
VIRTUAL_MODALITY_GRAVADO  = "gravado"

VIRTUAL_CAMPAIGN_STATUS_RASCUNHO  = "rascunho"
VIRTUAL_CAMPAIGN_STATUS_PUBLICADA = "publicada"
VIRTUAL_CAMPAIGN_STATUS_PAUSADA   = "pausada"

VIRTUAL_SLOT_STATUS_LIVRE   = "livre"
VIRTUAL_SLOT_STATUS_TRAVADO = "travado"
VIRTUAL_SLOT_STATUS_VENDIDO = "vendido"

VIRTUAL_ORDER_STATUS_RESERVADO   = "reservado"     # soft lock ativo, link ainda não gerado
VIRTUAL_ORDER_STATUS_AGUARDANDO  = "aguardando"    # link gerado, esperando pagamento
VIRTUAL_ORDER_STATUS_PAGO        = "pago"
VIRTUAL_ORDER_STATUS_EXPIRADO    = "expirado"
VIRTUAL_ORDER_STATUS_CANCELADO   = "cancelado"     # conflito de horário; devolução aberta

VIRTUAL_PRODUCTION_STATUS_PENDENTE   = "pendente"
VIRTUAL_PRODUCTION_STATUS_GRAVANDO   = "gravando"
VIRTUAL_PRODUCTION_STATUS_FINALIZADO = "finalizado"

VIRTUAL_SOFT_LOCK_MINUTES = 15          # FR-017
VIRTUAL_SLOT_MINUTES      = 10          # duração fixa da chamada

VIRTUAL_RETRY_MAX_ATTEMPTS   = 3        # FR-056 — tentativas nos minutos 0, 1 e 2
VIRTUAL_RETRY_INTERVAL_MIN   = 1
VIRTUAL_VIDEO_MAX_BYTES      = 250 * 1024 * 1024   # FR-038d
VIRTUAL_ACCESS_SESSION_MIN   = 30       # FR-044c — expira por inatividade
```

---

## 1. `virtual_campaigns` — a oferta publicada

| Campo | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | |
| `catalog_character_id` | FK → `catalog_characters.id` | NOT NULL, `ondelete="RESTRICT"`; personagem precisa estar ativo na criação (FR-001) |
| `slug` | String(160) | NOT NULL, UNIQUE — endereço público (FR-011) |
| `status` | String(20) | `rascunho` \| `publicada` \| `pausada`, default `rascunho` (FR-007) |
| `title` | String(200) | NOT NULL — título público |
| `intro_html` | Text | texto de apresentação (FR-002) |
| `tolerance_terms` | Text | termos de tolerância (FR-002) |
| `faq_json` | Text | JSON `[{pergunta, resposta}]` — renderizado só no fim da página (FR-013) |
| `cover_url` | String(500) | foto de capa, via `save_file` (FR-002) |
| `whatsapp_phone` | String(20) | destino da deflexão do FAQ (FR-013) |
| `price_live` | Numeric(12,2) | NOT NULL — chamada ao vivo (FR-003) |
| `price_recorded` | Numeric(12,2) | NOT NULL — vídeo gravado (FR-003) |
| `price_gift` | Numeric(12,2) | NOT NULL, default 0 — adicional do presente (FR-003) |
| `recorded_capacity` | Integer | NOT NULL — capacidade finita de vídeos (FR-005) |
| `recorded_sold` | Integer | NOT NULL default 0 — consumido (FR-033) |
| `recorded_delivery_days` | Integer | NOT NULL — prazo do vídeo, exibido na landing (FR-040) |
| `talent_id` | FK → `talents.id` | nullable — talento da pré-escala (FR-031) |
| `figurino_sheet_id` | FK → `figurino_sheets.id` | nullable — default vem do personagem |
| `max_reservations_per_origin` | Integer | NOT NULL default 5 — teto anti-abuso ajustável (FR-020b/020d) |
| `reservation_window_minutes` | Integer | NOT NULL default 60 — janela do teto (FR-020b) |
| `created_at` / `updated_at` | DateTime | |

**Dinheiro é `Numeric(12,2)`, sempre** (Princípio IX, plan.md "Regra monetária desta feature"). A
InfinitePay exige centavos inteiros, mas isso é característica do fornecedor: a conversão vive
apenas dentro de `app/integracoes/infinitepay_client.py`. Nenhuma coluna, nenhum campo de JSON e
nenhuma variável do núcleo desta feature representa dinheiro em centavos — é o mesmo tipo que
`CalendarEvent.sale_value` já usa, e é o que impede duas representações de dinheiro convivendo.

**Índices**: `UNIQUE(slug)`, `ix_virtual_campaigns_status`.

**Transições**: `rascunho → publicada → pausada ⇄ publicada`. Publicar exige preços, capacidade,
prazo e capa preenchidos. Pausar não invalida reservas em curso (edge case da spec).

---

## 2. `virtual_campaign_slots` — estoque de horários

| Campo | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | |
| `campaign_id` | FK → `virtual_campaigns.id` | NOT NULL, `ondelete="CASCADE"` |
| `start_at` | DateTime | NOT NULL — naive São Paulo, igual ao resto do sistema |
| `status` | String(20) | `livre` \| `travado` \| `vendido` (FR-017) |
| `locked_until` | DateTime | nullable — fim do soft lock |
| `order_id` | FK → `virtual_orders.id` | nullable — dono atual |
| `created_at` | DateTime | |

**Índices**: `UNIQUE(campaign_id, start_at)` — é o que torna a geração de horários idempotente
(FR-004); `ix_virtual_campaign_slots_status`; `ix_virtual_campaign_slots_start_at`.

**Concorrência (R4)**: toda mudança de posse passa por `with_for_update()` nesta linha. Um slot é
disponível quando `status == 'livre'` **ou** (`status == 'travado'` e `locked_until < now`) — a
segunda condição é o que faz a expiração ser preguiçosa e correta mesmo se a varredura atrasar.

**Regra de exclusão**: só slots `livre` sem `order_id` podem ser removidos (FR-008).

---

## 3. `virtual_orders` — o pedido

| Campo | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | |
| `campaign_id` | FK → `virtual_campaigns.id` | NOT NULL |
| `slot_id` | FK → `virtual_campaign_slots.id` | nullable — vídeo gravado não tem horário |
| `modality` | String(12) | `ao_vivo` \| `gravado` |
| `status` | String(16) | ciclo acima |
| `order_nsu` | String(64) | NOT NULL **UNIQUE** — nosso id na InfinitePay e chave de idempotência (R1/R4) |
| `public_token` | String(43) | NOT NULL UNIQUE — página do pedido sem login (FR-044); mesmo padrão de `CalendarEvent.feedback_token` |
| `child_name` | String(120) | NOT NULL (FR-014) |
| `child_age` | Integer | NOT NULL |
| `behavior_notes` | Text | dicas da família (FR-014) |
| `contact_phone` | String(20) | NOT NULL, normalizado só dígitos — chave do limite anti-abuso (FR-020a) |
| `contact_phone_display` | String(30) | |
| `contact_email` | String(180) | NOT NULL — canal dos avisos automáticos (FR-014/035) |
| `delivery_address` | String(300) | obrigatório só com presente (FR-014/015) |
| `gift_item_id` | FK → `acervo_3d_items.id` | nullable — peça escolhida (FR-016) |
| `price_interaction` | Numeric(12,2) | congelado na reserva (FR-022) |
| `price_gift` | Numeric(12,2) | congelado na reserva |
| `total_value` | Numeric(12,2) | soma congelada — é o valor conferido na reconsulta, após o cliente converter o `paid_amount` da operadora de centavos para reais (FR-027b) |
| `locked_until` | DateTime | espelha o slot; existe também para o gravado |
| `payment_url` | String(500) | link devolvido pela InfinitePay |
| `invoice_slug` | String(120) | `slug` da fatura |
| `transaction_nsu` | String(120) | id da transação, vem no webhook/retorno |
| `paid_at` | DateTime | |
| `event_id` | FK → `calendar_events.id` | nullable — preenchido na efetivação (FR-029) |
| `meet_url` | String(500) | **link da sala** entregue à família (R2 — *não* é `google_html_link`) |
| `meet_pending` | Boolean | default False — sala ainda não materializou (FR-037) |
| `origin_hash` | String(64) | hash da origem para o teto por janela (FR-020b); nunca o IP cru |
| `grace_until` | DateTime | nullable — fim da janela de retry (até 2 min) quando a operadora não responde na expiração (FR-018a) |
| `recheck_attempts` | Integer | default 0 — tentativas de reconsulta já feitas, teto em `VIRTUAL_RETRY_MAX_ATTEMPTS` (FR-056) |
| `expired_unverified` | Boolean | default False — expirou sem confirmação da operadora; explica a origem de um conflito posterior (FR-018b) |
| `access_attempts` | Integer | default 0 — erros de telefone na página do pedido (FR-044b) |
| `access_blocked_until` | DateTime | nullable — bloqueio temporário após erros consecutivos (FR-044b) |
| `created_at` / `updated_at` | DateTime | |

**Índices**: `UNIQUE(order_nsu)`, `UNIQUE(public_token)`, `ix_virtual_orders_status`,
`ix_virtual_orders_campaign_id`, `ix_virtual_orders_contact_phone`, `ix_virtual_orders_created_at`.

**Privacidade**: `child_name`, `child_age` e `delivery_address` são dados de criança. Só saem em
endpoints autenticados ou na página do próprio pedido (token). Nunca em listagem pública.

---

## 4. `virtual_payment_notifications` — auditoria e idempotência

| Campo | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | |
| `order_id` | FK → `virtual_orders.id` | nullable — aviso órfão também é registrado (FR-034) |
| `order_nsu` | String(64) | como veio no aviso |
| `transaction_nsu` | String(120) | **UNIQUE** — barra o reprocessamento de reentrega (R4) |
| `raw_payload` | Text | corpo bruto recebido |
| `secret_ok` | Boolean | o endereço secreto conferia (FR-027a) |
| `recheck_result` | String(20) | `paid` \| `unpaid` \| `divergent` \| `unavailable` \| `error` (FR-027b/c/d) |
| `recheck_payload` | Text | resposta do `payment_check` |
| `outcome` | String(24) | `efetivado` \| `duplicado` \| `recusado` \| `conflito` \| `retido` \| `orfao` |
| `message` | Text | motivo legível para a equipe |
| `created_at` | DateTime | |

**Nada é descartado** — inclusive chamadas com segredo errado (viram `secret_ok = False`,
`outcome = 'recusado'`), que é como a equipe percebe uma investida.

---

## 5. `virtual_media_deliveries` — a fila de produção

| Campo | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | |
| `order_id` | FK → `virtual_orders.id` | NOT NULL UNIQUE — uma entrega por pedido pago |
| `status` | String(16) | `pendente` \| `gravando` \| `finalizado` (FR-047) |
| `due_date` | Date | nullable — prazo do gravado, derivado de `recorded_delivery_days` (FR-041) |
| `video_path` | String(500) | caminho **interno** do arquivo no storage — nunca devolvido ao cliente (FR-038e, R3) |
| `video_mime` | String(60) | tipo do arquivo, para servir o stream corretamente |
| `video_size_bytes` | BigInteger | usado no limite de tamanho (FR-038d) |
| `video_published_at` | DateTime | |
| `last_upload_error` | Text | motivo da última falha, exibido na linha (FR-038c) |
| `updated_by_id` | FK → `users.id` | nullable |
| `created_at` / `updated_at` | DateTime | |

**Invariante (FR-048)**: `status == 'finalizado'` exige `video_path` não nulo **para modalidade
gravada**. Entregas ao vivo finalizam sem vídeo.

**Privacidade (FR-038e)**: `video_path` é caminho interno, não URL divulgável. O vídeo só sai pelo
endpoint que valida. O `subfolder` usado no `save_file` fica fora de qualquer prefixo servido
estaticamente — se o arquivo puder ser baixado pela URL do storage, a validação dupla vira enfeite.

---

## 6. `virtual_refund_requests` — devolução rastreada

| Campo | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | |
| `order_id` | FK → `virtual_orders.id` | NOT NULL |
| `amount` | Numeric(12,2) | NOT NULL — o que foi pago |
| `reason` | String(40) | `conflito_horario` (único motivo automático nesta versão) |
| `status` | String(16) | `pendente` \| `concluida` (FR-043) |
| `invoice_slug` / `transaction_nsu` | String | o que a equipe precisa para achar a cobrança no painel |
| `resolved_by_id` | FK → `users.id` | nullable |
| `resolved_at` | DateTime | nullable |
| `created_at` | DateTime | |

Existe porque a InfinitePay não publica API de estorno (R1): o sistema garante rastreio e cobrança,
a execução é humana.

---

## 7. `virtual_campaign_acervo` — peças liberadas (associação)

Tabela de associação `campaign_id` × `acervo_3d_item_id`, `UNIQUE(campaign_id, acervo_3d_item_id)`,
CASCADE dos dois lados. Nada além do vínculo (FR-006).

---

## 8. `virtual_order_notifications` — avisos enviados

| Campo | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | |
| `order_id` | FK → `virtual_orders.id` | NOT NULL |
| `kind` | String(24) | `compra_confirmada` \| `video_pronto` \| `cancelamento` |
| `sent_ok` | Boolean | |
| `error_message` | Text | nullable (FR-039c) |
| `created_at` | DateTime | |

**`UNIQUE(order_id, kind)` — é a trava de idempotência do aviso (FR-028a).** A linha é gravada na
**mesma transação** que decide enviar, antes do disparo; a violação de unicidade é o que impede o
segundo envio (FR-028b). Sem isso, a reentrega do aviso de pagamento manda "compra confirmada"
quantas vezes a operadora repetir.

Reenvio deliberado pela equipe, quando existir, apaga a linha ou grava outra com `kind` próprio —
nunca burla a restrição.

---

## Configuração nova em `SiteSetting`

| Campo | Uso |
|---|---|
| `infinitepay_handle` | `handle` das chamadas (R1) |
| `infinitepay_webhook_token` | segredo do path do webhook, revogável sem deploy (FR-027a) |

Nenhum segredo em código ou repositório (Princípio: `.env` / config centralizada).

---

## Relacionamentos

```text
CatalogCharacter ──1:N──> VirtualCampaign ──1:N──> VirtualCampaignSlot
                                │                          │ 1:1 (posse)
                                │ N:N ──> Acervo3DItem      ▼
                                └────1:N───────────> VirtualOrder ──1:1──> VirtualMediaDelivery
                                                          │  │  │
                                    CalendarEvent <──1:1──┘  │  └──1:N──> VirtualPaymentNotification
                                          │                  │  └──1:N──> VirtualOrderNotification
                                          ├──> EventRole     └──0:1──> VirtualRefundRequest
                                          └──> Event3DGift (pendência de impressão)
```

## Efetivação — o que acontece em uma transação (FR-027 a FR-033)

1. `with_for_update()` no slot (quando ao vivo).
2. Insere `VirtualPaymentNotification`; violação de unicidade → já processado, encerra com `200`.
3. `payment_check` na operadora; o cliente converte o `paid_amount` (centavos) para `Decimal` em
   reais e o núcleo confere `paid` e o valor contra `total_value`.
4. Slot indisponível → `VirtualRefundRequest` + pedido `cancelado` + e-mail; **não** cria evento.
5. Caminho feliz: slot `vendido` → `CalendarEvent` (`event_type='VIRTUAL'`, `source='platform'`,
   `sale_value`) com `conferenceData` → `EventRole` pré-escalado → `Event3DGift` se houver presente
   → `recorded_sold += 1` se gravado → `VirtualMediaDelivery` → `VirtualOrderNotification`
   (`compra_confirmada`) gravado **antes** do disparo, na mesma transação (FR-028b).
6. Qualquer exceção desfaz tudo — inclusive o registro do aviso, que volta a permitir o envio na
   próxima tentativa; a notificação fica registrada como `retido`.

`source='platform'` + `event_type='VIRTUAL'` é também a marca que exclui o evento da sincronização
com a agenda externa (FR-029a, R9).
