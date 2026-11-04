# Pesquisa — 334 De qual anúncio veio cada cliente

As decisões de produto vieram do dono (spec, Clarifications); aqui está só o "como".

## R1 — O que a Meta manda

- **WhatsApp** (Cloud API): a primeira mensagem de quem clica num anúncio "click to WhatsApp" traz `messages[].referral`:
  `source_type` (`ad` ou `post`), `source_id` (o id do anúncio ou da publicação), `source_url`, `headline`, `body`,
  `media_type`, `image_url`/`video_url`/`thumbnail_url` e `ctwa_clid`.
- **Instagram** (mensageria pela Página): `messaging[].referral` no aviso de abertura da conversa (sem mensagem) e, às
  vezes, `messaging[].message.referral` junto da mensagem. Os campos são `source` (`ADS` para anúncio), `type`
  (`OPEN_THREAD`), `ad_id`, `ref` e `ads_context_data.{ad_title, photo_url, video_url, post_id}`.
- **Decisão**: só `ad`/`ADS` vira contato por **anúncio** (consulta e atribuição). `post` vira **publicação** e o
  resto do Instagram vira **outro**: os dois ficam registrados, sem consulta e sem origem de anúncio.

## R2 — Onde a captura entra (na transação do aviso)

- **WhatsApp**: `aviso_ops._gravar_recebida`, depois de inserir a mensagem nova. Com o `referral`, chama
  `anuncio_ops.registrar_contato(conversa, canal, chave=wamid, ...)`. O reenvio do mesmo aviso não insere a mensagem e
  não chega lá; a chave UNIQUE é a segunda trava.
- **Instagram**: `instagram_ops._processar_item`, com o `referral` do item ou da mensagem. A chave é o `mid` ou, sem
  mensagem, `ref:{igsid}:{timestamp}`. A abertura sem mensagem cria a conversa (e o perfil é buscado depois do commit,
  como na 330).
- **Sem chamada externa aqui.** A consulta à Meta é depois do commit (R4).

## R3 — A ficha

- `anuncio_ops.aplicar_na_ficha(conversa)` lê o primeiro e o último contato por **anúncio** da conversa:
  - **primeiro**: se a ficha ainda não tem `anuncio_origem_id`, grava o id e a data. Se a ficha não tem origem
    (`lead_origin`), grava "Anúncio do WhatsApp"/"Anúncio do Instagram", `utm_source=meta`, `utm_medium=anuncio` e a
    campanha, se já é conhecida;
  - **mais recente**: grava o id e a data se o contato é mais novo que o guardado.
- **Chamado** na captura (com a ficha já ligada) e sempre que a conversa ganha ficha: `ficha_ops.ligar`,
  `ficha_ops.ficha_para_envio` e a `aviso_ops._vincular_cliente`.
- **Orgânico** (`anuncio_ops.origem_organica`): só a ficha **nascida pela conversa** (a criação nova da 333, não a
  reaproveitada nem a escolhida) e sem anúncio na conversa ganha "WhatsApp"/"Instagram". A ficha antiga sem origem
  não ganha o canal (a conversa de hoje não diz como ela chegou).

## R4 — A consulta da campanha

- `app/integracoes/meta_anuncios_client.py`: `consultar_anuncio(conexao, anuncio_id)` →
  `GET /{anuncio_id}?fields=name,campaign{id,name}` pelo `whatsapp_client.requisitar` (o mesmo transporte, a mesma
  trava).
- **Token**: `META_ANUNCIOS_TOKEN` e, vazio, o `WHATSAPP_ACCESS_TOKEN` (o usuário do sistema do portfólio, que precisa de
  `ads_read` e da conta de anúncios). Sem os dois, desligado. A trava é a `WHATSAPP_SUPPRESS_SEND`: travado, nada sai.
- **Quando**:
  - depois do commit de cada aviso: `anuncio_ops.consultar_pendentes()` consulta os anúncios nunca consultados (um
    anti-join pequeno, até 10 por vez), sem passar listas pelos processadores;
  - na varredura: os que falharam há mais de 24 h, até 10 por vez.
- **Resultado**:
  - sucesso: grava o nome e a campanha em `anuncios_meta` e propaga a campanha para as fichas cujo primeiro anúncio é
    esse e que ainda não têm `utm_campaign`;
  - 404 ou código 100 da Graph (não existe): erro definitivo, sem nova tentativa;
  - permissão (10, 200, 190) e falha de rede: o motivo fica, e a varredura tenta de novo no dia seguinte.
- **Nunca levanta**: o aviso da Meta já foi gravado e fechado.

## R5 — O Desempenho

- `attributed_clients` passa a filtrar a janela por `coalesce(kommo_created_at, created_at)`: a ficha criada pela
  conversa entra (hoje só a do Kommo).
- `retornos_por_campanha(janela)`: os contatos por anúncio no período com campanha conhecida, de fichas que entraram
  na base **antes do dia do contato**, com os eventos fechados depois do contato. Ficam distintos por (ficha,
  campanha). A tabela de campanhas ganha `returns` e `return_events`, casando pelo nome normalizado como os leads.
- A tela ganha a coluna "Retornos" e o texto de ajuda passa a dizer de onde vêm os leads.

## R6 — Leitura

- `GET /api/conversas/<id>` ganha `anuncio`: o contato mais recente da conversa (`tipo`, `titulo`, `campanha`,
  `quando`), sem N+1 na lista. O cabeçalho mostra "Veio do anúncio "{título}" · {campanha}".
- `GET /api/clientes/<id>` ganha `origem`: `lead_origin`, `utm_campaign` e o primeiro e o mais recente anúncio (id,
  título, campanha, quando). A ficha mostra as linhas "Origem", "Primeiro anúncio" e "Anúncio mais recente".

## R7 — Migration e base

- `d334b2c4e6f8`, com `down_revision = "c333e1a5b7d9"` (head da 333):
  - `conversa_anuncios`;
  - `anuncios_meta`;
  - `clients.anuncio_origem_id`, `anuncio_origem_em`, `anuncio_recente_id` e `anuncio_recente_em`.
- Aditiva. A ordem de merge fica 325 → 328 → 330 → 332 → 333 → 334.

## R8 — Verificação

- Molde do `verify_333` (`MetaFalsa` para o WhatsApp e o Instagram). O dublê do `meta_anuncios_client.consultar_anuncio`
  conta as consultas e pode recusar (sem permissão) ou responder 404.
- O dia seguinte da varredura é simulado recuando o `consultado_em` por SQL.
