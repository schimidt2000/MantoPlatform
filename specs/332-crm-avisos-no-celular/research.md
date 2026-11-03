# Pesquisa — 332 Avisos das Conversas no celular

As decisões de produto vieram do dono (spec, Clarifications); aqui está só o "como".

## R1 — Web Push com VAPID, sem biblioteca de Web Push

- **Decisão**: o protocolo padrão do Web Push, com assinatura VAPID (ES256) e cifra `aes128gcm` (RFC 8291). Ele vale
  para os serviços de aviso do Chrome, Edge, Firefox e Safari, este no iOS 16.4+ com o app instalado.
- **Implementação**: a cifra (RFC 8291 sobre o RFC 8188) e a assinatura VAPID (RFC 8292) moram em
  `app/push/webpush.py`, sobre o `cryptography` e o `requests`.
- **Por que não o `pywebpush`**: ele traz o `py-vapid` e o `http-ece` junto, e instalar baixa código no `.venv`, que
  é compartilhado, e no build do Render.
- **`cryptography` fixado no `requirements.txt`** (`==46.0.7`). A convergência pegou: ele estava só no `.venv`
  (instalado pela sessão da feature 329, que fixa a mesma versão para a NFS-e), e nada do `requirements.txt` o
  puxava. Sem a linha, o `pip install` do Render não o traria e o `import` do `webpush` derrubaria o boot. No
  merge com a 329, fica uma linha só.
- **Prova da cifra**: uma cifra errada não dá erro em lugar nenhum, o aviso só não aparece. Por isso o verify usa o
  **vetor de teste oficial do RFC 8291 (apêndice A)**, e o resultado tem de bater byte a byte. Conferido em
  03/11, antes do núcleo.
- **Chaves**: `WEB_PUSH_VAPID_PUBLICA` e `WEB_PUSH_VAPID_PRIVADA` (env, vazias = desligado; Princípio XIV), mais
  `WEB_PUSH_CONTATO` com default `mailto:contato@mantoproducoes.com.br`.
  - O comando `flask webpush-chaves` gera um par novo e o imprime **só no terminal** de quem roda, para colar no
    Render. Nunca vai pelo chat.

## R2 — Onde nasce o aviso (sempre depois do commit)

- **Mensagem nova**: `aviso_ops.processar_aviso` já tem um "depois do commit" (mídias e perfis). Os processadores
  recebem um conjunto `chegadas` e juntam nele as conversas que **ganharam mensagem nova da cliente** (parâmetro
  explícito em vez de um terceiro item na tupla de retorno, que já mudava de forma entre WhatsApp e Instagram):
  - WhatsApp: `_gravar_recebida` com `mensagem_id` novo e tipo ≠ reação;
  - Instagram: `_chegou_da_cliente` (mensagem recebida com parte nova e toque em botão).

  Depois do commit, `celular_ops.avisar_mensagens(chegadas)` manda um aviso por conversa (o nome evita a confusão
  com o `aviso_ops`, que é o aviso da Meta). A ordem depois do commit passa a ser perfil → celular → mídia: o
  título precisa do nome do perfil, e a mídia pode levar minutos (SC-001). O reenvio do mesmo aviso
  não gera mensagem nova, então não toca (idempotência da 325).
- **Alerta de 15 min**: `equipe_ops.alertar_esperas` comita a rodada e então avisa quem recebeu cada alerta (o
  responsável, ou a equipe).
- **Transferência**: `equipe_ops.definir_responsavel` comita e então avisa o destino.
- **Por quê**: o aviso é chamada externa (Google/Apple/Mozilla). Dentro da transação, prenderia linha e poderia avisar
  algo que deu rollback (Princípio XIV e regime B da 272).

## R3 — Para quem

- **Destino**:
  - **Mensagem**: o responsável, se `responsavel_ativo`; senão, `membros_da_equipe()` (328).
  - **Alerta e transferência**: as mesmas pessoas do sino.
- **Filtro no envio**: só os aparelhos de quem ainda é da equipe (`e_da_equipe`). A pessoa desativada ou sem papel não
  recebe, mesmo com aparelho registrado.

## R4 — O aviso

- **Corpo** (JSON, que o service worker lê): `{"titulo", "corpo", "link", "tag"}`.
  - **Mensagem**: o título é o nome do contato, o corpo é a `ultima_previa` e a `tag` é `conversa-{id}`, para que os
    avisos da mesma conversa se substituam (`renotify`).
  - **Alerta e transferência**: o título do sino, e as `tag` `espera-{id}` e `transferida-{id}`.
- **Envio**: `push_ops.despachar(user_ids, aviso)` entrega numa thread própria, para o aviso não atrasar o webhook
  nem a tela (a transferência roda dentro da requisição). `WEB_PUSH_SINCRONO=true` entrega na hora (verify). Aviso
  perdido num deploy não volta (spec, casos de borda). `ttl` de 1 dia, urgência `high` para a mensagem, timeout de
  10 s.
- **Endereço do aparelho**: o servidor faz POST no `endpoint` que o navegador mandou. Só os serviços de aviso
  conhecidos são aceitos (`fcm.googleapis.com`, `*.push.services.mozilla.com`, `*.notify.windows.com`,
  `*.push.apple.com`), em https, senão 422: o registro não pode virar um jeito de o servidor chamar um endereço
  qualquer (SSRF).
  - 404/410 → apaga o aparelho;
  - outra falha → log e segue.
  - Atualiza `ultimo_aviso_em`.

## R5 — Trava

- **Decisão**: `_suppress_push()` em `app/config.py`, derivada do host do banco como as outras. O escape é
  `WEB_PUSH_ALLOW_LOCAL=true`.
- **No envio**: travado → log `[push] travado` e nada sai. O registro do aparelho funciona mesmo travado, para a tela
  poder ser conferida.
- **Trava forçada**: `WEB_PUSH_SUPPRESS=true` trava em qualquer ambiente (inclusive produção), para desligar os
  avisos sem apagar as chaves. Não estava no pedido; ficou registrada na convergência.

## R6 — Navegador

- **`frontend/apps/internal/public/`**, que o Vite copia para a raiz do `dist` e o `server.js` serve na raiz:
  - `manifest.webmanifest`: nome "Plataforma Manto", nome curto "Manto", `display: standalone`, `start_url: /`
    (o manifesto vale para a Plataforma inteira: o Casting que instalar não pode cair numa tela sem acesso), cores
    da casa e ícones 192/512 com `purpose: any` (o "M" encosta nas bordas: recortado em círculo, perderia as
    pontas);
  - os ícones `icone-192.png`, `icone-512.png` e `apple-touch-icon.png`, tirados do ícone que a casa já usa
    (`app/static/apple-touch-icon-app.png`, o "M" branco sobre o roxo);
  - `sw.js`: `push` → `showNotification(titulo, {body, tag, renotify, data: {link}, icon})`; `notificationclick` →
    foca a aba da Plataforma e navega para o link (só caminhos da própria Plataforma), ou abre uma nova;
    `pushsubscriptionchange` → registra a assinatura nova.
- **`index.html`**: `<link rel="manifest">`, `apple-touch-icon` e `theme-color`.
- **Tela**: `AvisosNoCelular` (botão + diálogo) no cabeçalho da lista de Conversas.
  - Mostra o estado: ativo, inativo, negado, sem suporte, iPhone fora da Tela de Início, desligado.
  - "Ativar avisos": registra o SW, pede a permissão, `pushManager.subscribe` com a chave pública e `POST`.
  - "Desativar": `unsubscribe` e `DELETE`.

## R7 — Migration e base

- `push_assinaturas`, com `down_revision = "a330c4e8f1b2"` (head da 330). A ordem de merge fica 325 → 328 → 330 → 332.
