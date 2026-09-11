# Hotfix 263b — O proxy que guardava para sempre o vídeo que ninguém mais assistia

**Branch**: `263b-hotfix-proxy-vazamento-sockets` (da `main`) · **Created**: 2026-09-11
**Status**: **EM PRODUÇÃO desde 2026-09-11 03:14** (merge `2914e98`) — `verify_263b.py` 21/21 ·
**Migration**: nenhuma

Filho da **263-endurecimento-concorrencia** (26/08/2026), que criou o `proxyTimeout` do proxy
Node e isentou a mídia com prazo zero — a isenção é o que deixou este vazamento sem limite.

## O pedido, nas palavras do dono

"Surgiu um problema no site. A memória está em uso super alto. Fui tentar subir um vídeo e
aplicar moldura, e aí travou em 43% e ficou parado. Achei um pouco estranho esse uso da memória
crescente ao longo do dia. Talvez tenha alguma coisa acumulando e não saindo. Agora eu não
consigo nem acessar direito a plataforma: quando eu clico, ela demora anos para carregar a página
de login. E se esse processo de colocar a moldura no vídeo for muito custoso eu posso abandonar."
(gráficos do Render de 10/09/2026, ~21h50; frontend em 100% de 512 MB subindo em escada desde as
10h, backend com picos de p90 de 10 min.)

## O que foi encontrado

- **Render, aba Events do `manto-frontend`:** "Instance failed — Ran out of memory (used over
  512MB)" às 22:06 de 10/09; o site voltou sozinho com o reinício. O **mesmo evento em 08/09 às
  11:11**, antes de a 297 subir (09/09 16:46). O vazamento é anterior à 297; ela o acelerou (3,7
  dias → 29 h) porque a página pública passou a tocar vídeo.
- **`manto-frontend` por SSH, 01:03 UTC, minutos antes da morte:** `memory.current` 536 670 208 de
  536 870 912; `memory.stat` anon 96 MB, file 1,6 MB, **sock 432 MB**; `/proc/net/sockstat` TCP
  inuse 142, mem 106 582 páginas; processo `node server.js` com **85 MB de RSS**, 147 descritores
  de socket, 27 de `apps/public/dist/index.html` e 6 de `apps/internal/dist/index.html` abertos;
  `memory.events max` = 726 446, `oom_kill` 0. A memória era buffer de socket TCP no kernel, não
  heap do Node.
- **`manto-backend`:** ocioso — gunicorn com 3-4 threads por worker, todas em `futex`/`ep_poll`,
  `sock` de 40 KB, cgroup em 812 MB de 2 GB, nenhum `ffmpeg`, fila de conversão vazia. A moldura
  da 297 não tem nada a ver com o incidente; não há o que abandonar.
- **Log do frontend na última hora:** `socket hang up` e `Client network socket disconnected
  before secure TLS connection was established` em `/api/3d/nfc/<id>/entregas/<id>/media`,
  `/api/nfc/abertura/video`, `/api/nfc/<code>`; o upload das 21:50 morreu com `write ECONNRESET`
  — é o "travou em 43%": sem memória para socket, o contêiner nem fechava o TLS com o backend.
  Nas 24 h anteriores, **zero** linha `[proxy]`: o vazamento é silencioso.
- **Depois do reinício** a escada recomeçou: 185 MB de `sock` em 70 sockets às 02:14 de 11/09.
- O upload refeito pelo dono às 22:13 entrou e converteu em 1,5 min (entrega 15, tag 13).

## Causa

`frontend/server.js` faz o proxy com `http-proxy` 1.18.1, que só desliga a conexão com o Flask
em `req.on('aborted')` (`passes/web-incoming.js:146-148`). Em Node ≥ 16 o `req` de um GET é
consumido pelo `req.pipe(proxyReq)` e destruído no primeiro tick (autoDestroy do Readable); quando
o celular some no meio da **resposta**, o Node tenta destruir um `req` já destruído e nada é
emitido — nem `'aborted'`, nem `'error'`. O único objeto que sinaliza é `res` (`'close'` com
`writableFinished === false`), e ninguém o escutava. O `proxyRes.pipe(res)` vê o destino fechar,
faz `unpipe` e **pausa** `proxyRes`; pausado, o Node para de ler o socket do Flask (`readStop`), o
kernel enche a fila de recepção (autotuning até 6 MB) e ninguém a esvazia. Dois desfechos, ambos
reproduzidos: arquivo maior que o buffer → o Flask trava em backpressure e a conexão fica
ESTABLISHED para sempre; arquivo menor → o Flask termina e fecha, o FIN fica atrás dos dados não
lidos, o socket do proxy fica em CLOSE_WAIT com o payload dentro, e o lado do backend é descartado
pelo kernel em 60 s (`tcp_fin_timeout`) — por isso o backend estava limpo e só o frontend
acumulava. Em rota `/api` o `proxyTimeout` de 180 s limpava (é prazo de **inatividade** do socket
com o Flask); em mídia, com prazo 0 desde a 263, era para sempre.

Cada vídeo aberto e abandonado — a aba Vídeos de `/3d/tags` com dez players, a barra arrastada no
celular, a página `/nfc/<code>` fechada no meio — deixava até ~6 MB presos; 142 sockets × ~3 MB
é a escada do gráfico. **Upload abortado não vaza** (corpo incompleto ⇒ `'aborted'` dispara;
reproduzido com 3 uploads de 200 MB cortados aos 8 MB, zero socket sobrevivente).

Reprodução local, com o `server.js` da `main` intacto: 5 clientes abortando um download de 300 MB
aos 2 MB → 5 sockets do proxy com o backend ESTABLISHED aos 40, 90 e 200 s, `getConnections`=5 no
backend, zero linha de log; mesma coisa em `/api/x` → os 5 caem exatamente aos 180,0 s.

## O que muda (só `frontend/server.js`)

1. **`proxy.on('proxyReq')`** registra `res.once('close')` → `proxyReq.destroy()` quando
   `res.writableFinished` é false. Cobre também o cliente que some depois de mandar o corpo inteiro
   e antes de o Flask responder (ainda não há `proxyRes`).
2. **`res.on('pipe')`** no handler do servidor destrói qualquer origem pipada em `res` no mesmo
   caso: o `proxyRes` do Flask e o `ReadStream` do serve-handler (os 27 `index.html`).
3. **O caminho inverso, `proxyReq.once('close')` → `res.destroy()`** quando `res.writableEnded`
   é false: se é o Flask que some antes de terminar (prazo de inatividade, worker reciclado,
   deploy no meio de um download), o http-proxy destruía o `proxyRes` sem `end`, o pipe nunca
   chamava `res.end()` e o cliente ficava mudo — sem EOF nem erro, o player não refaz o `Range`.
   Achado pela verificação adversarial (duas lentes, independentes), pré-existente também em
   `/api`.
4. **Mídia deixa de ter prazo zero:** `MEDIA_PROXY_TIMEOUT_MS = 600_000` — dez minutos de
   inatividade do socket com o Flask. Transferência que flui nunca dispara. Vídeo pausado nem
   chega perto: medido no Chromium, o player enche o buffer, para de ler e fecha sozinho a conexão
   ociosa ~15 s depois; ao dar play reabre com `Range`. O prazo é rede de segurança, e quando
   dispara o cliente cai junto (item 3) para o player refazer o pedido. O comentário passa a dizer
   o que o prazo mede.
5. **`server.requestTimeout = 30 min`** e `headersTimeout = 60 s` explícitos: o default de 5 min
   do Node (desde o 18) respondia 408 a qualquer upload mais longo, por mais que o proxy estivesse
   isento — defeito latente da 297 (250 MB em 4G), nunca observado. Medido pela lente de
   regressão: upload pingando por 330 s dá 408 na `main` e 200 no branch.
6. **Linha `[vida]` a cada 5 min** no log: conexões de entrada, clientes que sumiram, RSS,
   recursos vivos por tipo e, no Linux, `sock` e total do cgroup — o que teria mostrado a escada
   na primeira hora.
7. Comentário em `SERVE_OPTIONS`: nunca ligar `etag: true` no serve-handler sem tratar o 304 (ele
   abre o `ReadStream` antes de comparar o ETag e, no 304, não pipa nem destrói — o gancho de
   `pipe` não alcança). Hoje o caminho não existe; é aviso, não mudança.

## Decisões

1. **Só o `server.js`.** Sem dependência nova, sem trocar o http-proxy, sem mexer em
   `BACKEND_PREFIXES`/`MEDIA_PATTERNS`/`/nfc`, sem `startCommand`. O `try/catch` do `proxy.web` e
   o `badGateway` ficam como estão.
2. **`res 'close'`, não `req 'close'` nem `req 'aborted'`.** `req 'close'` sai quando o corpo
   termina de ser lido e mataria toda requisição no começo da resposta; `'aborted'` está deprecado
   e é mudo depois de o corpo chegar inteiro.
3. **Dez minutos de inatividade para mídia, não zero nem 60 s.** Zero é o vazamento; abaixo de
   120 s cortaria celular trocando de rede. Um socket parado por 10 min é cliente morto (o
   Chromium fecha a conexão de mídia ociosa em ~15 s por conta própria) — e, quando o prazo
   dispara, o cliente é derrubado junto para o player refazer o pedido em vez de ficar mudo.
4. **`requestTimeout` finito (30 min), não zero.** Cobre a pior subida doméstica e mantém um teto;
   quem defende de requisição lenta maliciosa é o proxy do Render, na frente.
5. **Não mexer em `keepAliveTimeout` (5 s) nem em `BACKEND_URL`** neste commit: o idle do edge
   do Render é desconhecido e trocar para a rede privada mexe em `Host`, cookie e
   `X-Forwarded-*` — cada um merece a própria correção com sondagem.

## Verificação

`verify_263b.py` **21/21** contra o `server.js` do branch e **9/21** contra o da `main`
(`--antes`), falhando exatamente nos cenários de abandono e nas guardas de fonte:

| Cenário | `main` | branch |
|---|---|---|
| 5 downloads de mídia abandonados aos 2 MB | 5 ESTABLISHED com o backend aos 12 s | soltos em 0,0-0,5 s |
| backend já tinha terminado (0,6 MB, cliente lê 0,1 MB) | 5 CLOSE_WAIT | 0 |
| abandono em rota `/api` | 7 ESTABLISHED (180 s seria a única saída) | soltos em 0,0-0,5 s |
| cliente some depois do corpo, antes da resposta (`/api/lento`, 3 s) | backend responde para ninguém; CLOSE_WAIT | fecha antes de o backend responder (3,1 s) |
| backend morre no meio da resposta (`/api/morre`) | cliente mudo (3 s sem nada) | cliente vê EOF em 0,5 s |
| download de 40 MB por Range | 206, 41 943 040 bytes | idem |
| upload de 20 MB com backend lento (200 ms/MB) | 200, 20 971 520 bytes | idem |
| JSON, SPA `/` e `/nfc/<code>`, redirect `/f/` | ok | ok |
| cliente que abortou vira `[proxy]` 502 no log? | 0 linhas | 0 linhas |
| backend fora do ar (porta fechada) | 502 "Bad Gateway", SPA de pé | idem |

**Verificação adversarial** (workflow de três agentes independentes, cada um tentando refutar;
nenhum refutou): regressão — 870 requisições proxiadas + 1 150 estáticas sem erro, HEAD/304,
`Expect: 100-continue`, vídeo pausado 30 s e retomado, 502 real, 50 abandonos no serve-handler
(handles 249 no branch × 349 na `main`), 700 requisições em um socket sem `MaxListeners`, upload
de 330 s (408 na `main`, 200 no branch); eficácia — chunked sem `content-length`, PDF de 20 MB em
`/api`, backend que trava sem `end`, 200 abandonos em série e 50 em paralelo (sockets do proxy
voltam a 0 em 0,0 s, handles iguais), `proxyRes.destroy()` fechando o TCP em ~20 ms; produção —
APIs conferidas na doc do Node 20, regex de `sock` contra o formato real do `memory.stat`,
pós-corpo de `add_delivery` curto (a conversão é enfileirada), gthread do gunicorn deixa de
prender thread em `send` quando o cliente some. Achado comum das lentes: o cliente ficava mudo
quando o upstream era cortado — fechado pelo item 3 acima.

Não usa o `manto_local`: o defeito é do proxy Node, então o "banco" é `harness/upstream.js`, um
backend falso que conta o que acontece com cada conexão (`/__stats`). Roda o `server.js` de
verdade de dentro de `frontend/` (precisa dos `dist/`). Node local 24.18; produção roda **Node
20.20.2** (`NODE_VERSION=20` honrado; o `node -v` da sessão SSH mostra o 24 do sistema, não o do
processo) — a semântica de autoDestroy/`'aborted'` é a mesma desde o 16.

Não medido aqui: o prazo de 10 min em si (a lente de regressão o observou disparando aos
600 009 ms numa pausa de 630 s, antes do item 3); o comportamento em Node 20 (só há 24 na
máquina; os trechos internos usados são iguais nas duas linhas); se o gunicorn gthread aceita
upload > 5 min de parede (o `--timeout 120` é batimento do worker, não prazo de requisição).

## Como conferir em produção

Conferido logo após o deploy (11/09 03:16): contêiner novo com Node 20.20.2, 78 MB de memória e
4 KB de `sock`; 5 downloads do vídeo de abertura abandonados a 1 MB → `sock 0`, TCP inuse 2, 19
descritores no node em 5 s. Antes do push, o contêiner reiniciado às 22:06 já tinha voltado a
acumular 185 MB de `sock` em 70 sockets (02:14).

Por SSH no `manto-frontend` (`srv-da8nvsgn74is73ehe9a0`), depois de abrir e fechar a aba Vídeos
de `/3d/tags` algumas vezes: `egrep "^(sock|anon) " /sys/fs/cgroup/memory.stat` — `sock` volta a
poucos MB em segundos (antes só subia). No log do serviço, `[vida] conexoes=… sumiram=N rss=…
cgroup=… sock=…` a cada 5 min, com `sumiram` subindo e `sock` estável.

## Fora de escopo

- `BACKEND_URL` pela URL pública do backend: a rede privada do Render existe (hostname interno
  em Connect → Internal, mesma região e workspace) e tiraria o TLS e o edge do caminho — mudança
  de configuração com efeitos em `Host`/cookie/`X-Forwarded-*`; fica registrada no docs/05.
- `keepAliveTimeout` de 5 s do Node vs o idle do proxy do Render (risco de 502 esporádico por
  corrida) — só com sondagem.
- Cancelar o body do `fetch` do OG em 404/erro (higiene; o `AbortSignal.timeout` já limita).
- Medir os descritores de `index.html` do serve-handler (cobertos pelo gancho de `pipe`, sem
  cenário próprio no verify).
- Nenhuma tela muda; não há verificação de UI.
