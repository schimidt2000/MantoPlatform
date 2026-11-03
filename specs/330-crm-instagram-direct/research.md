# Pesquisa — 330 Instagram Direct na caixa de Conversas

Decisões da Phase 0. As de produto vieram do dono (spec, Clarifications); aqui está o "como". Documentação da Meta
consultada em 03/11/2026 (Instagram Messaging pela plataforma de mensagens: *get started*, *webhooks*, *conversation
routing*, *attachment upload*, *send message*). O que ela deixa em aberto está marcado **a confirmar no teste**.

## R1 — O caminho: mensageria do Instagram pela Página (decisão do dono)

- **Decisão**: Instagram Messaging na plataforma de mensagens da Meta, com o Instagram profissional da Manto ligado a
  uma Página. Host `graph.facebook.com`, versão fixa `v26.0` (a mesma do WhatsApp).
  - Permissões: `instagram_basic`, `instagram_manage_messages`, `pages_manage_metadata` e `pages_messaging`, mais a
    marca de resposta humana (R10). Entram no mesmo App Review do WhatsApp.
  - Token: o da Página, ou de um usuário do sistema do portfólio com a Página atribuída, que não vence.
- **Por quê**:
  - token sem renovação (o do login do Instagram vence em 60 dias);
  - **roteamento de conversa da Meta**: sem configuração, todos os apps conectados recebem os avisos, então o piloto
    convive com o Kommo; na virada, a Plataforma vira o app padrão no painel da Página;
  - o anúncio de origem (Click-to-Direct) chega no `referral`, para a Fase 3.
- **Alternativa**: API do Instagram com login do Instagram (`graph.instagram.com`) — descartada pelo dono.

## R2 — O webhook

- **Decisão**: endpoint próprio `GET|POST /api/webhooks/instagram` (`app/api/instagram_webhook.py`).
  - O app da Meta é o mesmo do WhatsApp, então o GET confere `WHATSAPP_VERIFY_TOKEN` e o POST o
    `X-Hub-Signature-256` com o `WHATSAPP_APP_SECRET`, pela mesma `assinatura_valida` do `whatsapp_webhook`.
  - O corpo válido é gravado cru na mesma tabela `whatsapp_avisos` e processado pelo mesmo `aviso_ops.processar_aviso`,
    que despacha pelo `object` do corpo (`"instagram"` → `instagram_ops`).
  - Ficam iguais ao WhatsApp a idempotência, o claim por linha e a varredura. Nenhuma tabela nova de aviso.
- **Por quê**: a URL do aviso é configurada por produto no painel da Meta (objeto `instagram`), e um endpoint separado
  deixa o 404 do canal desligado independente do WhatsApp. O pipeline cru → claim → varredura é o que garante nada
  perdido num deploy (FR-002); duplicá-lo seria a segunda fonte da mesma regra.
- **Filtro de conta**: `entry[].id` diferente de `INSTAGRAM_ACCOUNT_ID` é ignorado com log, como o `phone_number_id`
  do WhatsApp.

## R3 — Conversa, contato e perfil

- **Contato**: `conversas(canal="instagram", contato_id=<IGSID>)`, única pela `uq_conversas_canal_contato` da 325.
- **Pegadinha**: o IGSID é só dígitos, e a 325 calcula `telefone` e liga à ficha quando o contato é numérico. Por isso
  `conversa_do_contato` passa a derivar telefone e vínculo **só no canal WhatsApp**; sem isso, uma cliente do Instagram
  cairia na ficha de um telefone qualquer.
- **Perfil**: `GET /{IGSID}?fields=name,username` com o token da Página (campos **a confirmar no teste**). Guarda
  `nome_perfil` e `usuario` (coluna nova) e carimba `perfil_em`. Roda na criação da conversa e de novo quando o nome
  falta e o carimbo tem mais de 24 h (caso de borda "Perfil indisponível"). A busca do perfil sai **fora** da transação
  do aviso: falha de perfil nunca devolve o aviso à fila.

## R4 — Mensagens recebidas

O item `entry[].messaging[]` traz `sender.id`, `recipient.id`, `timestamp` (ms) e um entre: `message`, `reaction`,
`read`, `postback`, `referral`.
- **`message`**: `mid` é o `externo_id` (UNIQUE, `ON CONFLICT DO NOTHING` da 325). Texto em `message.text`.
- **Vários anexos numa mensagem** (até 10 fotos): uma `conversa_mensagens` por anexo, porque a mídia é 1:1 com a
  mensagem na 325. O primeiro usa o `mid`, os seguintes `"{mid}#{n}"`, e o texto fica no primeiro.
- **Tipos de anexo → tipo da casa**:
  - `image` → imagem;
  - `video` → vídeo;
  - `audio` → áudio;
  - `file` → documento;
  - `share`, `ig_reel`, `reel` e `story_mention` → texto pronto (casos de borda), com o link em `dados`;
  - `ephemeral` → texto pronto, sem link.
- **Resposta a story**: `reply_to.story` → "Respondeu ao seu story".
- **`is_unsupported`** → o texto do `TIPO_OUTRO` com "Abra no Instagram".
- **`is_deleted`** → a mensagem que já existe ganha o texto "Mensagem apagada pela cliente." (se ainda não existe,
  nasce assim).
- **Comprimento do id**: o `mid` do Instagram passa de 128 caracteres (é base64 longo). Por isso `externo_id` e
  `resposta_a` sobem para 255 na migration (só alarga o varchar; sem reescrita).

## R5 — Eco, reação e visto

- **Eco** (`message.is_echo`): o remetente é a conta da Manto e o destinatário é a cliente. Grava `ENVIADA` com origem
  `outro` ("Enviada por outro app": app do Instagram ou Kommo), encerra a espera e não atribui.
  - O eco da própria mensagem da Plataforma tem o mesmo `mid` que a resposta do envio devolveu, então não duplica.
  - **Corrida**: o eco pode chegar antes de o envio gravar o `mid`. Se houver envio da Plataforma em voo nesta conversa
    (pendente sem id, há menos de 5 min — o `_envio_em_voo` da 325), o aviso volta à fila
    (`MensagemAindaNaoGravada`).
- **Reação** (`reaction`): grava `TIPO_REACAO` com `externo_id = "reacao:{mid}:{timestamp}:{action}"`, com o texto
  "Reagiu com {emoji}" ou "Reação removida.". Não abre nem encerra a espera (regra da 328).
- **Visto** (`read.mid`): marca `lida` a enviada daquele `mid` e as enviadas anteriores da conversa que estão abaixo
  de `lida`, sem regredir. O Instagram não tem "entregue": a enviada vai de `enviada` a `lida`.

## R6 — Mídia recebida

- **Decisão**: `ConversaMidia` sem `externo_id`. O link do anexo fica no `dados` da mensagem, e `midia_ops.baixar_e_guardar`
  despacha pelo canal da conversa: no Instagram, baixa o `payload.url` com o mesmo `baixar_midia` (teto de 25 MB) e
  pega o MIME da resposta. A varredura da 325 retenta, com espaçamento e idade máxima de 48 h. O link da Meta assina e
  expira: o primeiro download é logo depois do commit.

## R7 — Envio

- **Texto**: `POST /{INSTAGRAM_PAGE_ID}/messages` com `{"recipient": {"id": IGSID}, "message": {"text": …}}`. A
  resposta traz `message_id`, gravado como `externo_id`. O texto vai até **1.000 bytes** em UTF-8 (limite da Meta),
  conferido no núcleo.
- **Arquivo**: o mesmo endpoint com upload direto, em multipart:
  - `recipient` (JSON);
  - `message` (JSON com `attachment.type` = `image`|`video`|`audio`|`file` e `payload.is_reusable=false`);
  - `filedata` (o arquivo).

  A codificação exata (multipart × JSON) fica **a confirmar no teste**. O cliente isola a montagem num lugar só.
  Formatos e tetos aceitos:
  - imagem png/jpeg/gif, até 8 MB;
  - vídeo mp4/ogg/avi/mov/webm, até 25 MB;
  - áudio aac/m4a/wav/mp4, até 25 MB;
  - PDF até 25 MB.
- **Garantias da 325**: chave de envio, mensagem gravada antes da chamada, falha que vira "não entregue" e trava local.
  Não há upload separado nem id de mídia guardado.
- **Arquitetura**: `envio_ops` continua o orquestrador (chave, reserva, cópia local, despacho, atribuição e espera da
  328). O que muda por canal sai para `app/conversas/canais.py`:
  - `pre_condicoes`;
  - `enviar_texto`;
  - `enviar_arquivo`;
  - `tipos_aceitos`;
  - `marcar_lida`.

  São dois objetos: WhatsApp (o código atual, movido sem mudar comportamento) e Instagram. O `verify_325` prova que o
  WhatsApp não mudou.

## R8 — Cliente HTTP do Instagram

- **Decisão**: `app/integracoes/instagram_client.py`, sem Flask, sobre o **mesmo transporte** do `whatsapp_client`.
  - O `_requisitar` vira público `requisitar`, e o nome antigo continua valendo.
  - Herda o timeout, o mapeamento do erro da Graph API (`WhatsappRecusou` com `code`) e a trava.
  - `ConexaoInstagram(base, versao, token, page_id, account_id, travada)`.
  - Funções: `enviar(conexao, corpo)`, `enviar_arquivo(conexao, destino, tipo, dados, mime, nome, tag)` e
    `perfil(conexao, igsid)`.
- **Por quê**: é a mesma Graph API, com os mesmos erros e limites. Um segundo cliente com outro tratamento de falha
  seria a segunda fonte (Princípio I).

## R9 — Configuração e trava

- **Variáveis novas**, todas vazias por padrão, o que deixa o canal desligado (Princípio XIV):
  - `INSTAGRAM_ACCESS_TOKEN`;
  - `INSTAGRAM_PAGE_ID` (envio);
  - `INSTAGRAM_ACCOUNT_ID` (filtro do aviso).
- **Ligado**: as três, mais o `WHATSAPP_APP_SECRET` e o `WHATSAPP_VERIFY_TOKEN` do app.
- **Log na subida**: `[instagram] ligado=… travado=…`. No `render.yaml`, com `sync: false`.
- **Trava**: a mesma `WHATSAPP_SUPPRESS_SEND` e o mesmo escape `WHATSAPP_ALLOW_LOCAL_SEND`. A trava é do "envio pela
  Meta", não de um canal: no `manto_local` o Instagram também não sai.
- **`conversas_ligadas`** de `/api/auth/me` passa a valer com **qualquer** canal ligado.

## R10 — A janela do Instagram

- **Decisão**: pela `ultima_recebida_em` (só a cliente reabre, como na 325):
  - até 24 h → envio normal;
  - de 24 h a 7 dias → envio com `"messaging_type": "MESSAGE_TAG", "tag": "HUMAN_AGENT"`;
  - depois de 7 dias → 409 `janela_fechada` com o texto do cenário 12.
- **Tela**: a API passa a dizer `janela: "aberta" | "humana" | "fechada"`. `janela_aberta` continua verdadeiro em
  "aberta" e "humana" no Instagram; o contrato da 325 não muda para o WhatsApp.
- **Permissão**: a marca exige "Human Agent" no App Review. Até sair, a Meta recusa (código **a confirmar**), e a
  mensagem fica "não entregue" com o motivo "A Meta ainda não liberou a resposta depois de 24 horas no Instagram.".
  Os códigos de erro do Instagram entram no `MOTIVO_DO_ERRO`.

## R11 — Áudio gravado para o Instagram

- **Decisão**: o Instagram não aceita ogg nem webm em áudio. Para uma conversa do Instagram, o webm do Chrome e o ogg
  do Firefox viram **m4a (AAC)** com o ffmpeg:
  - `-vn -c:a aac -b:a 96k -f ipod`, arquivo temporário e 60 s de timeout, em `midia_ops.audio_para_m4a`, irmã da
    `webm_para_ogg` da 328;
  - aqui recodifica: o encoder `aac` nativo existe no ffmpeg LGPL local e no 5.1.9 do Render;
  - o mp4 do Safari vai direto.
- **No WhatsApp nada muda** (webm → ogg com `voice`).

## R12 — Tela

- **Lista**: ícone do canal (`MessageCircle` no WhatsApp, `Instagram` do `lucide-react` 0.462, que existe) e filtro
  "Canal: Todos · WhatsApp · Instagram" (`?canal=` no endereço), mostrado só com os dois canais ligados
  (`canais_ligados` na lista).
- **Conversa**:
  - "@usuário" no lugar do telefone;
  - aviso da janela humana;
  - depois de 7 dias, só o aviso, sem campo;
  - sem "Enviar modelo";
  - o clipe aceita só os tipos do Instagram.
- **Gravador**: o mesmo da 328; a conversão é no servidor.

## R13 — Migration e base

- A base é a branch 328 (fora da `main`): `down_revision = "f328b2d4e6a1"`.
- A migration:
  - `conversas` ganha `usuario` (String 64) e `perfil_em` (DateTime);
  - `conversa_mensagens.externo_id` e `resposta_a` vão de 128 para 255.
- O merge segue a ordem 325 → 328 → 330.
