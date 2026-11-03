# Pesquisa — 332 Avisos das Conversas no celular

As decisões de produto vieram do dono (spec, Clarifications); aqui está só o "como".

## R1 — Web Push com VAPID e `pywebpush`

- **Decisão**: o protocolo padrão do Web Push, com assinatura VAPID (ES256) e cifra `aes128gcm` (RFC 8291). Ele vale
  para os serviços de aviso do Chrome, Edge, Firefox e Safari, este no iOS 16.4+ com o app instalado.
- **Biblioteca**: `pywebpush==2.0.3`, fixa no `requirements.txt`. Traz `py-vapid` e `http-ece`; o `cryptography` já
  está na casa.
- **Alternativa**: implementar a cifra à mão sobre o `cryptography`. Foi descartada porque uma cifra errada não dá erro:
  o aviso simplesmente nunca aparece, e o verify (com dublê) não pegaria.
- **Chaves**: `WEB_PUSH_VAPID_PUBLICA` e `WEB_PUSH_VAPID_PRIVADA` (env, vazias = desligado; Princípio XIV), mais
  `WEB_PUSH_CONTATO` com default `mailto:contato@mantoproducoes.com.br`.
  - O comando `flask webpush-chaves` gera um par novo e o imprime **só no terminal** de quem roda, para colar no
    Render. Nunca vai pelo chat.

## R2 — Onde nasce o aviso (sempre depois do commit)

- **Mensagem nova**: `aviso_ops.processar_aviso` já tem um "depois do commit" (mídias e perfis). Os processadores
  passam a devolver também as conversas que **ganharam mensagem nova da cliente**:
  - WhatsApp: `_gravar_recebida` com `mensagem_id` novo e tipo ≠ reação;
  - Instagram: `_gravar_recebida`, `_gravar_postback`.

  Depois do commit, `avisos_ops.avisar_mensagens(conversa_ids)` manda um aviso por conversa. O reenvio do mesmo aviso
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
- **Envio**: `ttl` de 1 dia, urgência `high` para a mensagem, timeout de 10 s.
  - 404/410 → apaga o aparelho;
  - outra falha → log e segue.
  - Atualiza `ultimo_aviso_em`.

## R5 — Trava

- **Decisão**: `_suppress_push()` em `app/config.py`, derivada do host do banco como as outras. O escape é
  `WEB_PUSH_ALLOW_LOCAL=true`.
- **No envio**: travado → log `[push] travado` e nada sai. O registro do aparelho funciona mesmo travado, para a tela
  poder ser conferida.

## R6 — Navegador

- **`frontend/apps/internal/public/`**, que o Vite copia para a raiz do `dist` e o `server.js` serve na raiz:
  - `manifest.webmanifest`: nome "Plataforma Manto", nome curto "Manto", `display: standalone`, `start_url:
    /conversas`, cores da casa, ícones 192/512 e `purpose: any maskable`;
  - os ícones `icone-192.png`, `icone-512.png` e `apple-touch-icon.png`;
  - `sw.js`: `push` → `showNotification(titulo, {body, tag, renotify, data: {link}, icon})`; `notificationclick` →
    foca a aba da Plataforma e navega para o link, ou abre uma nova.
- **`index.html`**: `<link rel="manifest">`, `apple-touch-icon` e `theme-color`.
- **Tela**: `AvisosNoCelular` (botão + diálogo) no cabeçalho da lista de Conversas.
  - Mostra o estado: ativo, inativo, negado, sem suporte, iPhone fora da Tela de Início, desligado.
  - "Ativar avisos": registra o SW, pede a permissão, `pushManager.subscribe` com a chave pública e `POST`.
  - "Desativar": `unsubscribe` e `DELETE`.

## R7 — Migration e base

- `push_assinaturas`, com `down_revision = "a330c4e8f1b2"` (head da 330). A ordem de merge fica 325 → 328 → 330 → 332.
