# Pesquisa — 325 Conversas (WhatsApp)

Decisões da Phase 0. Fonte de cada fato externo ao lado; fatos do código com arquivo. Pesquisa feita
em 30/10/2026 (docs da Meta + leitura do repositório). O que não foi confirmado está marcado.

## R1 — API e versão

- **Decisão**: Cloud API da Meta, chamada direto (`https://graph.facebook.com/<versão>`), com a versão
  fixada em `WHATSAPP_GRAPH_VERSION` (default real no `app/config.py`, revisão uma vez por ano —
  `docs/PLANO_CRM_PROPRIO.md` §9).
- **Por quê**: é a API que o Kommo já usa para a Manto (widget `whatsapp_cloud_api`, Fase 0); integrar
  direto dispensa intermediário. Versão fixa evita mudança silenciosa de payload.
- **Alternativas**: intermediário (360dialog) — mensalidade e dependência, reserva da Fase 4; API não
  oficial — descartada (banimento).

## R2 — Webhook: autenticação e corpo

- **Decisão**: GET responde o `hub.challenge` quando `hub.mode=subscribe` e o `hub.verify_token`
  confere (`compare_digest`); POST exige `X-Hub-Signature-256: sha256=<hex>` = HMAC-SHA256 do corpo
  **bruto** com o App Secret. Inválido, ausente ou módulo desligado → **404** sem efeito. Corpo lido
  com teto (`request.stream.read(teto+1)`, 256 KB) — mesmo cuidado do C-12 da ClickSign
  (`app/api/clicksign_webhook.py`).
- **Por quê**: é o contrato da Meta; o 404 segue a casa (não confirma existência). O teto de 256 KB
  cabe com folga um lote de avisos de texto (a mídia não vem no corpo, só o id).
- **Segredo**: App Secret em **env** (não em `site_settings` como a ClickSign): a Meta não rotaciona
  sozinha, e o segredo fora do banco não vai para backup nem espelho.

## R3 — Gravar cru, responder já, processar fora

- **Decisão**: o POST válido grava `whatsapp_avisos` (`pendente`), comita e responde 200; o
  processamento roda numa thread (`WHATSAPP_AVISO_SINCRONO=True` processa na requisição — costura do
  verify, como `CLICKSIGN_AVISO_SINCRONO`). Claim atômico `UPDATE … SET estado='processando',
  tentativas=tentativas+1 WHERE id=:id AND estado='pendente'` (molde do `_reivindicar_aviso` da 310,
  `docs/04` §4). Varredura (thread atrás de `MANTO_SEM_THREADS` + comando `flask
  whatsapp-reprocessar`) a cada 60 s pega `pendente` com mais de 30 s e `processando` parado há
  10 min; 48 h ou 10 tentativas → `descartado`.
- **Por quê**: a Meta reenvia o que não teve 200 rápido e o deploy mata threads; gravar antes torna a
  perda impossível e o reenvio inofensivo (idempotência em R5). Download de mídia (até 100 MB) não cabe
  dentro da requisição.
- **Alternativas**: processar na requisição (InfinitePay da `main` — a 310 trocou por isto
  justamente pelo risco); fila (Redis/RQ) — infraestrutura nova sem necessidade no volume da Manto
  (~4.500 recebidas/mês, Fase 0).

## R4 — Formato do aviso que o processador entende

Lê `entry[].changes[]` com `field == "messages"` (e `smb_message_echoes` na coexistência);
`value.metadata.phone_number_id` precisa ser o `WHATSAPP_PHONE_NUMBER_ID` configurado (outro número →
ignorado e registrado, para um app com dois números nunca misturar). Dentro de `value`:

- `contacts[]` → `wa_id` e `profile.name` (nome de perfil);
- `messages[]` → `id` (wamid), `from`, `timestamp` (epoch s), `type` e o bloco do tipo (`text.body`,
  `image|audio|video|document|sticker{id, mime_type, sha256, caption, filename}`, `location`,
  `contacts`, `reaction{message_id, emoji}`, `interactive`, `button`, `unsupported`/`unknown`),
  `context.id` (citação), `referral` (anúncio — guardado em `dados`, usado na Fase 3);
- `statuses[]` → `id`, `status` (`sent`/`delivered`/`read`/`failed`), `timestamp`, `recipient_id`,
  `errors[]{code, title, message, error_data.details}`.
- Eco da coexistência (`smb_message_echoes`): ver R12.

Tipos sem exibição nesta fase viram `texto` curto em pt-BR (`constantes.TEXTO_DO_TIPO`), nunca erro.

## R5 — Idempotência

- **Decisão**: `UNIQUE(externo_id)` em `conversa_mensagens` (o wamid) e `UNIQUE(canal, contato_id)`
  em `conversas`, ambos com `INSERT … ON CONFLICT DO NOTHING` + releitura (PostgreSQL; armadilha 10
  do `docs/00` §6: idempotência por restrição, não por fluxo). Envio: `UNIQUE(chave_envio)` — a mesma
  chave devolve a mensagem existente sem chamar a Meta (FR-018). Status: aplicar é monotônico (ordem
  em `data-model.md`), então reaplicar o mesmo aviso é inofensivo.
- **Status antes da mensagem**: se o `id` do status não existe ainda (corrida envio × aviso), o
  aviso inteiro volta a `pendente` com `erro="mensagem ainda não gravada"` e a varredura o refaz em
  1 min — sem tabela extra, porque tudo no aviso é idempotente.
- **Varredura entre workers**: as 3 threads (uma por worker do gunicorn) podem varrer juntas sem
  coluna nova no `site_settings`: o claim é **por linha** (aviso e mídia), atômico no `UPDATE … WHERE
  estado='pendente'`, então dois workers nunca processam a mesma linha. Custa só um `SELECT` barato
  por worker por minuto — evita mexer em tabela existente (Princípio IV).

## R6 — Mídia recebida

- **Decisão**: no processamento, para cada mensagem com mídia: grava a mensagem e a `ConversaMidia`
  (`pendente`) primeiro, comita, e só então `GET /<media_id>` (devolve `url`, `mime_type`,
  `file_size`) → `GET url` com `Authorization: Bearer` → `save_file` na subpasta `conversas/AAAA/MM/`
  → grava em `CONVERSAS_MEDIA_FOLDER/AAAA/MM/<uuid>.<ext>` → `guardada`. Falha → continua `pendente`
  com `erro`; a varredura retenta (o id da mídia vale por dias, a url só minutos — por isso a url é
  pedida de novo a cada tentativa). Download por `stream=True` + `iter_content` com teto, molde de
  `clicksign_client.baixar` (`app/integracoes/clicksign_client.py:209-231`). Teto de segurança:
  **25 MB** guardados (cobre imagem, áudio, vídeo e quase todo documento); acima → `falhou` com
  "Arquivo acima de 25 MB. Abra no celular." (dívida para a Fase 4, junto com o volume real).
- **Sem compressão**: imagem de conversa é prova (comprovante, print), não vitrine — os bytes são
  gravados como vieram.

## R7 — Onde guardar e servir a mídia

- **Decisão**: pasta **irmã** de `uploads`, `CONVERSAS_MEDIA_FOLDER` (default
  `instance/conversas_midia`, criada em `create_app` como `NFC_MEDIA_FOLDER`, `app/__init__.py:717`),
  servida só por `GET /api/conversas/midia/<id>` (gate `_pode_conversas`, `send_file(...,
  conditional=True)`, 404 sem papel ou sem arquivo — molde `nfc_read.py:125-154`). A pasta entra em
  `_MEDIA_SUBDIRS` de `app/backup_drive.py:31`, senão fica fora do backup.
- **Por quê**: `save_file` com `USE_S3=true` devolve URL de **bucket público** (`app/storage.py:266`)
  e `/uploads/<path>` é rota servida; foto, áudio e comprovante de cliente não podem depender de o
  endereço não vazar. É exatamente o motivo da 205 e da 261 (`app/config.py:428-438`). O despacho
  compartilhado de `/uploads` não é tocado (Princípio IV).
- **Custo anotado**: o backup de mídia no Drive tem orçamento (`_KEEP_MEDIA`, ~15 GB da conta de
  serviço). No número de teste o volume é desprezível; o volume real entra na decisão da Fase 4
  (dívida no `docs/05`).

## R8 — Envio

- **Ordem**: (1) gate; (2) configurado? senão 503 `nao_configurado`; (3) trava local? senão 409
  `envio_travado`; (4) janela (texto e mídia; modelo dispensa) senão 409 `janela_fechada`;
  (5) `INSERT` da mensagem `pendente` com `chave_envio` (conflito → devolve a existente) e commit;
  (6) chamada à Meta **sem trava de linha**; (7) grava `externo_id` + `enviada`, ou `falhou` com
  código/motivo; atualiza a prévia da conversa.
- **Mídia enviada**: `save_file` da cópia local (para a conversa exibir) + upload à Meta
  (`POST /<phone_number_id>/media`, multipart) → id → mensagem com esse id. Tipos aceitos pela Meta
  por MIME (imagem JPEG/PNG; documento PDF/Office/txt; áudio aac/amr/mpeg/mp4/ogg-opus; vídeo mp4/3gpp)
  — lista em `constantes`, validada antes de gravar (422 com `fields.arquivo`).
- **Cliente HTTP** `app/integracoes/whatsapp_client.py`: sem Flask, token e trava por parâmetro,
  `timeout=(5, 30)` (download de mídia `(5, 120)`), exceções `WhatsappRecusou` (4xx, com `code`),
  `WhatsappIndisponivel` (timeout/5xx/429 — "não sei") e `WhatsappTravado` (subclasse de
  indisponível), molde de `infinitepay_client.py`/`clicksign_client.py`.
- **Indisponível no envio**: a mensagem fica `falhou` com "Não foi possível enviar. Tente
  novamente." — nesta fase não há reenvio automático (a pessoa decide reenviar; mandar sozinho
  minutos depois poderia chegar fora de contexto).

## R9 — Janela de 24 h

`janela_aberta` = última **recebida** há menos de 24 h (`conversas.ultima_recebida_em`, UTC). O eco do
celular e as enviadas **não** reabrem a janela (só a cliente reabre). Fora dela: texto e mídia
recusados no núcleo (409) e o botão some na tela, trocado por "Enviar modelo". A Meta também recusa
(erro 131047, "re-engagement") — se acontecer por relógio, a mensagem fica `falhou` com o motivo
traduzido.

## R10 — Códigos de erro → motivo em pt-BR

Mapa em `constantes.MOTIVO_DO_ERRO` (os não mapeados: "A Meta recusou a mensagem (código N).").
Mínimo: 131047 janela fechada; 131026 número sem WhatsApp ou não alcançável; 131051 tipo não
aceito; 130429 / 131056 limite de envio — aguarde; 190 token vencido — avise o Superadmin; 100
parâmetro inválido; 132000/132001 modelo inexistente ou variáveis erradas. (Lista conferida contra a
referência da Meta na pesquisa; ver R13 para o que não se confirmou.)

## R11 — Nono dígito

- **Decisão**: `app/conversas/telefone.py` com `variantes_de_telefone(digitos) -> list[str]`, montada
  **sobre** `chave_telefone` (`app/contratos/contratos_ops.py:167`, que já reduz a DDD + últimos 8
  dígitos e casa número com e sem o 9 — Princípio I: a regra do nono dígito tem uma fonte só): da
  chave `DDD+8` saem `55+DDD+9+8` e `55+DDD+8`, as duas formas que `normalize_phone` grava em
  `Client.phone`. Vínculo: `Client.phone IN variantes` (usa o índice único de `phone`). Para **responder**,
  usa-se o `contato_id` exatamente como a Meta mandou (é o endereço que ela aceita); `telefone` da
  conversa guarda a forma com o 9 (a do `Client.phone`).
- **Por quê**: contas antigas de WhatsApp no Brasil chegam com 12 dígitos; sem as variantes, a ficha
  da cliente nunca ligaria.

## R12 — Coexistência (eco do app do celular)

- **Decisão**: tratar `field == "smb_message_echoes"` como mensagem **enviada**, `origem="celular"`,
  sem autor, situação `enviada`, idempotente pelo mesmo `UNIQUE(externo_id)`. Não reabre a janela
  (R9). O formato exato é conferido na pesquisa (R13); o verify usa o formato documentado.
- **Por quê**: a Fase 4 liga o número principal em coexistência; o dado precisa ter onde morar desde
  já (sem migration na virada).

## R13 — Pendências da pesquisa externa

Itens que dependem da referência da Meta e são confirmados antes do `tasks.md`: versão vigente da
Graph API (R1); formato do `smb_message_echoes` (R12); efeito do novo modelo de contas (WhatsApp
account × Messaging account, 23/09/2026) nas chamadas de um app integrado direto; política de
reenvio do webhook. Resultado registrado abaixo, em "Confirmações".

## R14 — Tela

- **Rota** `/conversas` (app interno), item de menu "Conversas" visível para COMERCIAL/SUPERADMIN; a
  tela trata `configurado: false` com estado vazio explicativo ("O WhatsApp ainda não foi
  configurado. Peça ao Superadmin para preencher as chaves no Render."). O menu decide por
  `isVisible(user)` (`lib/navigation.tsx:53-77`), que só conhece o `AuthUser` de `/api/auth/me`
  (`serialize_user`, `app/api/auth.py:31-49`): o payload ganha **`conversas_ligadas: bool`** (campo
  novo, opcional no TS — armadilha 21; ausente = item oculto), e o item aparece para
  COMERCIAL/SUPERADMIN com o módulo ligado. É o único toque num contrato compartilhado, e é aditivo.
- **Layout**: duas colunas no desktop (lista | conversa); no celular, uma de cada vez (a conversa
  abre por cima, com "Voltar" — `LinkVoltarParaLista`, feature 320).
- **Atualização**: `refetchInterval` 5 s na lista e 4 s na conversa, `refetchIntervalInBackground:
  false`; ao abrir, `POST …/lida`.
- **Envio otimista**: a mensagem aparece com relógio (situação `pendente`) e é substituída pela
  resposta; erro mantém o texto no campo (Princípio V).
- **Áudio**: `<audio controls>`; vídeo: `<video controls>`; imagem: `Foto` + `VisualizadorDeArquivo`;
  documento: `LinkDeArquivo` (feature 320 — nunca outra aba).

## Confirmações (pesquisa externa de 30/10/2026; D/ = developers.facebook.com/documentation/business-messaging/whatsapp/)

- **R1 — versão**: **v26.0** (lançada em 29/07/2026, sem data de fim; a v25.0 vale até 29/07/2028).
  Os exemplos atuais da documentação usam a v26.0. A partir da v24, o status perdeu o objeto
  `conversation` e o `pricing` vem em um só aviso. Default: `WHATSAPP_GRAPH_VERSION = "v26.0"`
  (fonte: developers.facebook.com/docs/graph-api/changelog).
- **R2 — assinatura**: `X-Hub-Signature-256` = HMAC-SHA256 do corpo com o App Secret, confirmado.
  Reenvio: qualquer resposta diferente de 200 é falha; a Meta tenta de novo na hora e depois com
  frequência decrescente por **até 7 dias**, gerando duplicatas (dedup pelo wamid, R5). O payload
  pode ter até 3 MB. Alguns webhooks não chegam com o app em modo Dev (`D/webhooks/overview`). O teto
  de 256 KB continua: um lote de texto nunca chega perto, e mídia não vem no corpo. Acima disso, 413
  e a Meta reenvia (registrado no log).
- **BSUID (novo, desde abril de 2026)**: os avisos trazem `contacts[].user_id`,
  `messages[].from_user_id` e `statuses[].recipient_user_id` (`"BR.123…"`), e `profile.username`.
  Quem usa nome de usuário e não conversou com a Manto nos últimos 30 dias pode chegar **sem
  telefone**. Envio por BSUID: campo `"recipient"` no lugar de `"to"` (`D/business-scoped-user-ids/`).
  → **Decisão**: `conversas` ganha `contato_bsuid` (String(64), null). O `contato_id` é o `wa_id`
  quando ele vem; senão, o BSUID. O envio usa `to` com o `wa_id` e, sem ele, `recipient` com o BSUID.
  O telefone não é obrigatório.
- **Status**: os valores são `sent`, `delivered`, `read`, **`played`** (nota de voz ouvida) e
  `failed`. → `played` conta como `lida`. Erros de conta chegam em `value.errors` e só vão para o log.
- **Mídia**: o `GET /{media-id}` devolve `url`, `mime_type`, `sha256` e `file_size`. A url **expira
  em 5 min** e exige Bearer. O id recebido vale **7 dias** (o de upload, 30), cobrindo com folga o
  abandono em 48 h. A partir de nov/2025 o aviso pode trazer a `url` direto; continuamos pedindo pelo
  id, que é o caminho garantido. Limites para envio: imagem JPEG/PNG 5 MB; áudio
  aac/amr/mpeg/mp4/ogg-opus 16 MB; vídeo mp4/3gpp 16 MB; documento 100 MB; figurinha WebP. Upload
  multipart com `file`, `type` e `messaging_product`.
- **Envio**: `POST /{phone-number-id}/messages` devolve `contacts[0].wa_id` e `messages[0].id`. O
  texto vai até 4096 caracteres. "Marcar como lida": `{"messaging_product":"whatsapp","status":"read",
  "message_id":…}` devolve `{"success":true}`.
- **R9/R10 — 131047**: pelo que a comunidade relata, a API aceita o envio e a recusa chega depois,
  num status `failed` (não está documentado como síncrono). → A recusa no núcleo (409) continua sendo
  a primeira barreira. O `failed` assíncrono é coberto pelo `_aplicar_status`. Códigos acrescentados
  ao mapa: 131049, 131050, 131048, 131052, 131053, 131000, 131008, 131009, 131005/10, 200, 4, 80007,
  368/131031, 131042, 133010, 132012, 132015, 132016, 132018 (`D/support/error-codes`).
- **R11 — nono dígito**: não há documentação oficial. A comunidade confirma `wa_id` e `from` de
  celular brasileiro **sem o 9** (12 dígitos) e diz que enviar com o 9 funciona. → A decisão R11 vale
  como está: o `wa_id` recebido é a chave e o endereço, e o vínculo aceita as duas formas.
- **R12 — eco**: `field = "smb_message_echoes"`, com `value.message_echoes[]` e
  `{from, to, id, timestamp, type, text|image|video|document}`. Também chegam os tipos `revoke`
  (apagou) e `edit` (editou, com `original_message_id`). O contato é o `to`
  (`D/webhooks/reference/smb_message_echoes`). → `revoke` e `edit` viram mensagem de texto curto
  ("Mensagem apagada pelo celular." / "Mensagem editada pelo celular.") e não alteram a original
  nesta fase.
- **Novo modelo de contas**: a URL de templates **não muda** (`/{waba-id}/message_templates`, em que o
  id passa a denotar a Messaging account). Na Fase 1, nada muda no código. O `messaging_account_id`
  só é exigido quando o token enxerga várias Messaging accounts no mesmo número, o que **não** é o
  caso do número de teste. **O roteamento das mensagens recebidas entre várias Messaging accounts
  segue sem documentação**: é o teste obrigatório da porta C, antes da Fase 4.
- **Coexistência**: confirmado de novo que exige Solution Partner ou Tech Provider, via Embedded
  Signup, e que limita a 20 msg/s, sem grupos e com os aparelhos vinculados desconectados. A
  sincronização de histórico (até 180 dias, em fases) só pode ser pedida uma vez, até 24 h depois do
  onboarding. Fica para a Fase 4.
- **Número de teste**: +1 555 grátis, para até 5 destinatários verificados. Token permanente via
  System User com `whatsapp_business_messaging`, `whatsapp_business_management` e
  `business_management` (`D/access-tokens`). Assinatura do webhook pelo painel do app ou por
  `POST /{waba-id}/subscribed_apps`.
