# Contratos — 330 Instagram Direct

Contrato da 325 em `specs/325-crm-whatsapp-fundacao/contracts/api.md` e o da 328 em
`specs/328-crm-equipe-na-caixa/contracts/api.md`; aqui só o que muda.

## `GET /api/webhooks/instagram` (público)

Desafio da Meta. Com `hub.mode=subscribe` e `hub.verify_token` igual ao `WHATSAPP_VERIFY_TOKEN` (`compare_digest`):
200 `text/plain` com o `hub.challenge`. Sem isso, ou com o canal desligado: **404**. Limite de `60/min`.

## `POST /api/webhooks/instagram` (público, assinado)

- **Assinatura**: `X-Hub-Signature-256: sha256=<hex>`, o HMAC-SHA256 do corpo bruto com o `WHATSAPP_APP_SECRET`.
- **Recusas**:
  - assinatura inválida, ausente ou canal desligado → **404**;
  - corpo acima de 256 KB → 413.
- **Válido**: grava em `whatsapp_avisos` e responde **200** sempre; processa fora da requisição (`WHATSAPP_AVISO_SINCRONO`
  = na hora). Limite de `300/min`.

## `GET /api/conversas`

- **Parâmetro novo** `canal=whatsapp|instagram`. Ausente = todos; outro valor → 422 `fields.canal`.
- **Resposta**: ganha `canais_ligados`, a lista de `"whatsapp"` / `"instagram"` ligados.
- **Cada conversa ganha**:
  - `canal` (já existia);
  - `usuario` (ou `null`);
  - `janela`: `"aberta"` | `"humana"` | `"fechada"`. No WhatsApp, `"humana"` nunca aparece.
- **`janela_aberta`**: segue valendo; no Instagram é verdadeiro em `"aberta"` e `"humana"`.
- **`janela_fecha_em`**: no Instagram, é o fim da janela atual (24 h ou 7 dias).

## `GET /api/conversas/<id>`

Mesmo cartão da lista, mais as mensagens. Mensagem do eco do Instagram: `origem: "outro"`.

## `POST /api/conversas/<id>/mensagens`

Envia pelo canal da conversa.

- **Instagram, texto**:
  - mais de 1.000 bytes → 422 `fields.texto` "A mensagem do Instagram passa de 1.000 caracteres.";
  - depois de 7 dias → 409 `codigo: "janela_fechada"`, com "Passaram 7 dias desde a última mensagem da cliente. Só
    ela pode retomar a conversa pelo Instagram.".
- **Instagram, arquivo**: tipo ou tamanho fora da regra do Instagram → 422 `fields.arquivo`:
  - "Tipo de arquivo não aceito pelo Instagram. Envie foto, vídeo, áudio ou PDF.";
  - "Arquivo acima de {N} MB para este tipo.".
- **Áudio** webm ou ogg numa conversa do Instagram → convertido para m4a; falha → 422 `fields.arquivo` com o texto da 328.
- **Canal desligado** → 503 `codigo: "nao_configurado"`, "O Instagram ainda não foi configurado.".

## `POST /api/conversas/<id>/modelo`

Numa conversa do Instagram → 409 `codigo: "sem_modelos"`, "O Instagram não tem modelos. Responda dentro de 7 dias da
última mensagem da cliente.".

## `POST /api/conversas/<id>/lida`

No Instagram, zera `nao_lidas` e **não** chama a Meta (sem "marcar como visto" nesta fase).

## Corpo enviado à Meta (dublê do verify)

- **Texto**: `POST /{INSTAGRAM_PAGE_ID}/messages` com `{"recipient": {"id": IGSID}, "message": {"text": "…"}}`. Na
  janela humana, acrescenta `"messaging_type": "MESSAGE_TAG", "tag": "HUMAN_AGENT"`.
- **Arquivo**: o mesmo endpoint, com `recipient`, `message.attachment.type` (`image`|`video`|`audio`|`file`), os
  mesmos campos de tag e o arquivo.
