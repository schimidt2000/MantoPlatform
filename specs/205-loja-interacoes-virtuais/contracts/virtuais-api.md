# Contrato de API — Loja de Interações Virtuais (feature 205)

**Convenções**: `specs/144-migracao-react-spa/contracts/api-conventions.md`. Erros sempre no
envelope `{"error": {"message": "...", "fields": {...}}}` via `app.api_utils.json_error`.

**Valores monetários trafegam em reais decimais** (ex.: `190.00`), nunca em centavos — nenhum campo
desta API termina em `_cents`. Centavos existem apenas dentro de
`app/integracoes/infinitepay_client.py`, na conversa com a operadora. A formatação para exibição e
a máscara de digitação são do front, exclusivamente via `@manto/money` (Princípio IX e plan.md
"Regra monetária desta feature").

Módulos novos: `app/api/virtuais_public.py` (sem login), `app/api/virtuais_read.py`,
`app/api/virtuais_write.py` (com login), `app/api/virtuais_webhook.py` (segredo no path). Todos
registrados em `app/api/__init__.py`.

---

## 1. Superfície pública (sem autenticação)

### `GET /api/virtuais/campanhas/<slug>`

Landing da campanha. Só responde se `status == 'publicada'`.

```json
{
  "slug": "papai-noel-2026",
  "title": "Chamada com o Papai Noel",
  "character": { "name": "Papai Noel", "photo_url": "/uploads/..." },
  "cover_url": "/uploads/virtual_covers/abc.jpg",
  "intro_html": "<p>...</p>",
  "tolerance_terms": "...",
  "faq": [{ "pergunta": "...", "resposta": "..." }],
  "whatsapp_phone": "+5511999998888",
  "price_live": "150.00",
  "price_recorded": "90.00",
  "price_gift": "40.00",
  "recorded_available": 12,
  "recorded_delivery_days": 7,
  "gift_items": [{ "id": 3, "name": "Bota do Noel", "photo_url": "/uploads/..." }]
}
```

`404` campanha inexistente ou em rascunho · `410` pausada/despublicada (FR-007).

### `GET /api/virtuais/campanhas/<slug>/horarios?date=YYYY-MM-DD`

Só horários **disponíveis**: `livre`, ou `travado` com `locked_until` vencido, e `start_at` no
futuro (edge case "horário no passado"). Nunca expõe quem reservou.

```json
{ "slots": [{ "id": 88, "start_at": "2026-12-20T14:10:00" }] }
```

### `POST /api/virtuais/campanhas/<slug>/reservar`

Cria o pedido e aplica o soft lock. **Idempotente por clique**: o front envia `client_token` e uma
repetição devolve o mesmo pedido em vez de travar um segundo horário (FR-026).

```json
{
  "client_token": "uuid-do-navegador",
  "modality": "ao_vivo",
  "slot_id": 88,
  "child_name": "Marina",
  "child_age": 6,
  "behavior_notes": "Adora dinossauros; irmão chama Téo.",
  "contact_phone": "(11) 99999-8888",
  "contact_email": "mae@exemplo.com",
  "gift_item_id": 3,
  "delivery_address": "Rua X, 100 - São Paulo/SP"
}
```

**201**

```json
{
  "public_token": "AbC...43",
  "order_nsu": "205-000431",
  "locked_until": "2026-11-02T10:15:00",
  "total_value": "190.00",
  "payment_url": "https://checkout.infinitepay.com.br/manto?lenc=..."
}
```

| Status | Quando |
|---|---|
| `400` | validação — `fields` aponta o campo (FR-025). Endereço exigido só com `gift_item_id` |
| `409` | horário tomado na disputa (US2 cenário 5) ou capacidade de gravado esgotada (FR-023) |
| `429` | limite por telefone (FR-020a) ou teto por origem (FR-020b) — `message` explica qual |
| `502` | InfinitePay indisponível ao gerar o link; a reserva é desfeita e o horário volta |

O `429` por telefone traz o pedido existente para a família retomar:
`{"error": {"message": "...", "existing_order_token": "AbC..."}}`.

### `GET /api/virtuais/pedidos/<public_token>` — resumo mínimo

Sem validação ainda. Devolve **apenas** o suficiente para a família confirmar que chegou ao pedido
certo (FR-044a). Nenhum dado de criança, endereço, sala ou vídeo aqui.

```json
{
  "status": "pago",
  "modality": "ao_vivo",
  "start_at": "2026-12-20T14:10:00",
  "total_value": "190.00",
  "locked_until": null,
  "payment_url": null,
  "requires_verification": true,
  "phone_hint": "•••• 8888",
  "campaign": { "slug": "papai-noel-2026", "title": "...", "whatsapp_phone": "..." }
}
```

### `POST /api/virtuais/pedidos/<public_token>/verificar`

Validação dupla (FR-044a): `{"phone": "(11) 99999-8888"}`. Confere contra o telefone da compra,
comparando só dígitos. Em caso de acerto, abre uma sessão curta de acesso (FR-044c).

| Status | Quando |
|---|---|
| `200` | telefone confere — devolve o pedido completo (abaixo) |
| `401` | telefone não confere; `attempts_left` no corpo |
| `429` | erros consecutivos estouraram o limite; `blocked_until` no corpo (FR-044b) |

**200** — só aqui aparecem os dados sensíveis:

```json
{
  "child_name": "Marina",
  "child_age": 6,
  "behavior_notes": "Adora dinossauros...",
  "delivery_address": "Rua X, 100 - São Paulo/SP",
  "meet_url": "https://meet.google.com/abc-defg-hij",
  "meet_pending": false,
  "video_url": "/api/virtuais/pedidos/AbC.../video",
  "recorded_due_date": "2026-12-27",
  "gift": { "name": "Bota do Noel", "photo_url": "..." }
}
```

`meet_url` só com pedido `pago`. Pedido `expirado` devolve `status: "expirado"` para a tela convidar
a escolher outro horário preservando os dados.

### `GET /api/virtuais/pedidos/<public_token>/video`

Serve o vídeo **sob validação a cada requisição** (FR-038e) — exige a sessão de acesso aberta pelo
`/verificar`. Suporta `Range` para o player poder buscar no vídeo.

`401` sem sessão válida · `404` sem vídeo publicado.

**Regra inegociável**: a URL do arquivo no armazenamento nunca é devolvida ao cliente, e o
`subfolder` dos vídeos fica fora de qualquer caminho servido estaticamente. Devolver a URL direta
anularia toda a validação dupla.

### `GET /api/virtuais/enderecos/autocomplete?q=`

Variante pública de `/api/maps/address-autocomplete` (que exige login — R5). Throttle por origem,
restrito ao Brasil, chave do Google só no servidor (Princípio XII.4). Mesmo formato de resposta do
endpoint interno — o `GoogleAddressInput` promovido a `@manto/ui` aceita a URL por prop.

---

## 2. Webhook (segredo no path, sem sessão)

### `POST /api/webhooks/infinitepay/<token>`

`token` = `SiteSetting.infinitepay_webhook_token`, revogável sem deploy.

O endpoint **só** valida o segredo, desserializa e delega a
`app/marketing/virtuais_ops.processar_notificacao_pagamento()` — nenhuma regra de negócio na rota
(Princípio III e diretriz 1 do usuário).

Corpo recebido (contrato da operadora — [research.md](../research.md) R1):

```json
{
  "invoice_slug": "abc123",
  "amount": 19000,
  "paid_amount": 19000,
  "installments": 1,
  "capture_method": "pix",
  "transaction_nsu": "uuid",
  "order_nsu": "205-000431",
  "receipt_url": "https://...",
  "items": []
}
```

**Sempre responde `200 {"success": true, "message": null}`** — inclusive em duplicata, pedido
inexistente ou conflito. `400` faz a operadora reenviar em loop, e reenviar não conserta nada
desses casos; o que precisa de atenção humana é sinalizado pelo registro, não pelo status HTTP.

Única exceção: segredo inválido → `404` (não `403`, para não confirmar a existência do endereço).

**O corpo não decide nada.** Ele identifica o pedido; a liberação depende do `payment_check`
(FR-027a/b).

---

## 3. Admin — campanhas (login + `SUPERADMIN`/`COMERCIAL`)

| Método | Rota | Uso |
|---|---|---|
| `GET` | `/api/virtuais/campanhas` | lista com vendidos, faturado e horários restantes (FR-009) |
| `POST` | `/api/virtuais/campanhas` | cria (multipart — capa) |
| `GET` | `/api/virtuais/campanhas/<id>/admin` | detalhe completo |
| `PATCH` | `/api/virtuais/campanhas/<id>` | edita textos, preços, prazo, limites |
| `POST` | `/api/virtuais/campanhas/<id>/publicar` | `{"status": "publicada" \| "pausada" \| "rascunho"}` |
| `PUT` | `/api/virtuais/campanhas/<id>/acervo` | `{"item_ids": [1,2,3]}` — peças liberadas (FR-006) |
| `POST` | `/api/virtuais/campanhas/<id>/horarios` | gera slots |
| `DELETE` | `/api/virtuais/horarios/<slot_id>` | remove slot livre |

**Geração de horários** (FR-004) — `{"date": "2026-12-20", "start": "14:00", "end": "18:00"}` →
`{"created": 24, "skipped": 0}`. `skipped` conta os que já existiam: reexecutar é seguro.

`DELETE` de slot reservado/vendido → `409` explicando (FR-008).

Alterar preço nunca toca pedidos existentes (FR-022) — os valores estão congelados na linha do
pedido, não lidos da campanha.

---

## 4. Fila de Produção de Mídia (login + `SUPERADMIN`/`CASTING`/talento escalado)

### `GET /api/virtuais/producao?campaign_id=&date=&status=`

Uma linha por entrega, com tudo cruzado (FR-046):

```json
{
  "deliveries": [{
    "id": 12,
    "order_token": "AbC...",
    "modality": "ao_vivo",
    "start_at": "2026-12-20T14:10:00",
    "status": "pendente",
    "due_date": null,
    "child_name": "Marina",
    "child_age": 6,
    "behavior_notes": "Adora dinossauros...",
    "meet_url": "https://meet.google.com/abc-defg-hij",
    "meet_pending": false,
    "gift": { "status": "pendente", "item": { "name": "Bota do Noel", "photo_url": "..." } },
    "has_video": false,
    "last_upload_error": null,
    "whatsapp_url": "https://wa.me/5511999998888?text=..."
  }]
}
```

`gift` reusa `impressoes3d_ops.serialize_gift` — o payload do presente tem uma montagem só
(Princípio I).

### `PATCH /api/virtuais/producao/<id>`

`{"status": "gravando"}`. Marcar `finalizado` numa entrega gravada sem vídeo → `400`
`{"fields": {"video": "Envie o vídeo antes de finalizar."}}` (FR-048).

### `POST /api/virtuais/producao/<id>/video` (multipart)

Guarda o vídeo no armazenamento da plataforma, confirma que é reproduzível, finaliza a entrega e
dispara o e-mail (FR-038a/b). Erro ao guardar → `502` com `last_upload_error` preenchido; entrega
**não** finaliza e a família **não** é avisada (FR-038c). Extensão/tamanho inválidos → `400`
(FR-038d). A resposta devolve `has_video: true` — nunca o caminho do arquivo.

### `POST /api/virtuais/pedidos/<id>/sala` — regerar sala quando `meet_pending` (FR-037)

Cobre os dois modos de ficar sem sala: o evento existir no Google com a sala ainda não
materializada (reconsulta) e o evento **nunca** ter sido criado lá, com id local `virtual-local-`
(cria e reconcilia o id). Devolve `meet_url`, `meet_pending`, `meet_attempts` e
`meet_retry_esgotado`. Google fora responde `502`, nunca `500` — a varredura segue tentando.

### `POST /api/virtuais/pedidos/<id>/avisos/<kind>/reenviar` — reenviar aviso falhado (FR-039c)

Só reentrega aviso **já registrado e falhado**. Aviso já entregue responde `400`: reenviá-lo
mandaria um segundo e-mail à família, que é exatamente o que `UNIQUE(order_id, kind)` existe para
impedir. Nunca cria linha nova — criar aqui abriria um caminho paralelo ao fluxo automático.
Falha na reentrega responde `502` com o motivo, para o reforço manual por WhatsApp ser decisão
consciente.

---

## 5. Devoluções (login + `FINANCEIRO`/`SUPERADMIN`)

| Método | Rota | Uso |
|---|---|---|
| `GET` | `/api/virtuais/devolucoes?status=pendente` | lista o que a equipe precisa devolver (FR-043) |
| `PATCH` | `/api/virtuais/devolucoes/<id>` | `{"status": "concluida"}` após executar no painel da operadora |

Cada item traz `invoice_slug`, `transaction_nsu`, `amount` e contato da família — o
suficiente para achar a cobrança sem sair procurando.

Traz também a **origem do conflito** (FR-018b): `reason_label` em pt-BR e `sem_confirmacao`. Os
dois casos têm culpas opostas — a reserva que venceu e o horário liberado sem o sistema conseguir
confirmar o pagamento. No segundo, a família pode ter pago em dia; quem atende o telefone precisa
saber disso antes de dizer "sua reserva venceu".

---

## 6. Cliente da InfinitePay (`app/integracoes/infinitepay_client.py`)

Módulo isolado, sem Flask, para o contrato do fornecedor mudar num arquivo só:

```python
def criar_link_pagamento(*, handle, order_nsu, total: Decimal, description,
                         redirect_url, webhook_url, customer) -> dict
def consultar_pagamento(*, handle, order_nsu, transaction_nsu, slug) -> dict
```

**Este é o único arquivo do sistema que conhece centavos.** Recebe e devolve `Decimal` em reais;
converte para centavos inteiros ao falar com a operadora e converte o `paid_amount` de volta para
`Decimal` antes de entregar ao núcleo. Nenhuma outra camada precisa saber que a InfinitePay conta em
centavos (Princípio IX).

`consultar_pagamento` é a fonte de verdade. Distingue **não pago** (decisão de negócio) de
**indisponível** (`timeout`/`5xx` → pedido retido para nova tentativa, FR-027d) — confundir os dois
faria uma indisponibilidade da operadora liberar produto ou cancelar venda paga.
