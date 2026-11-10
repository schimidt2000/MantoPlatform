# Pesquisa — 340, caixa de avisos fora do deploy

Fontes: código em `96837811` (main), `specs/310-…/research.md`, documentação do Render lida em
10/11/2026 (`/docs/disks`, `/docs/deploys`, `/docs/health-checks`, `/docs/monorepo-support`,
`/docs/blueprint-spec`, `/docs/infrastructure-as-code`, `/docs/free`).

## R1 — Por que um serviço à parte (e não o backend sem disco agora)

**Decisão**: serviço `manto-avisos`, sem disco, que só guarda o aviso. O backend continua decidindo.

**Por quê**: o Render diz que "Adding a disk to a service prevents zero-downtime deploys" e que
"All service types redeploy with zero downtime, unless they attach a persistent disk" — o
container antigo segue recebendo até o novo passar no healthcheck. Um serviço sem disco e com
`healthCheckPath` nunca fica fora num deploy. O backend com disco fica (~1 min) até janeiro.

**Alternativas**: tirar o disco do backend agora (todos os uploads para R2/S3 — risco alto na
campanha; janeiro, decisão do dono); portão de deploy que fecha a loja a cada push (passo manual,
não resolve a causa); Hookdeck ou fila gerenciada (conta e dados de pagamento num terceiro);
apontar o aviso direto para a URL `onrender.com` do backend (tira o frontend do caminho, mas o
backend com disco continua caindo).

## R2 — O receptor guarda numa tabela própria, nunca em `virtual_payment_notifications`

**Decisão**: tabela nova `virtual_payment_inbox`; o backend drena chamando `registrar_aviso` /
`registrar_aviso_invalido` / `processar_aviso` sem mudá-las.

**Por quê**: `registrar_aviso` não é um `INSERT`. Ele reabre o registro não final, deixa o aviso
autenticado sobrescrever o registro que veio do retorno (forjável) e trata a corrida do
`UNIQUE(transaction_nsu)`. Escrever direto na tabela do aviso obrigaria a reimplementar isso fora do
backend — duas fontes da regra que protege dinheiro (Princípio I).

**Alternativa**: `INSERT … ON CONFLICT DO NOTHING` direto em `virtual_payment_notifications` —
perde o caso "retorno forjado antes do aviso" (o aviso autenticado seria descartado).

## R3 — O receptor não importa `app/`

**Decisão**: WSGI puro (biblioteca padrão) + `gunicorn==23.0.0` (versão da raiz) +
`psycopg[binary]==3.3.4`, em `servicos/avisos/` com `requirements.txt` próprio. SQL direto, conexão
curta por chamada (`connect_timeout=3`). O driver é o psycopg 3, não o `psycopg2-binary` da raiz:
o `.venv` de desenvolvimento (Python 3.14) tem só o psycopg 3.3.4, e o verify tem de exercitar o
mesmo driver que roda em produção (achado da implementação, 10/11).

**Por quê**: importar `app/` traz `create_app`, as threads de fundo, o Google e o e-mail; o build
instalaria o `requirements.txt` inteiro da raiz; e qualquer mudança no backend passaria a exigir
deploy do receptor. O receptor tem de ser o código que quase nunca muda. O que ele repete do
backend é pequeno e coberto pelo verify: a conferência do segredo (`token_do_aviso_valido`), o teto
de corpo (`_CORPO_MAXIMO`) e a regra do IP do cliente (`ipDoCliente` do `server.js`).

**Alternativa**: Flask mínimo — dependência a mais para três rotas; Node — o time e o resto da regra
do aviso são Python.

## R4 — Códigos de resposta

| Situação | Código | Motivo |
|---|---|---|
| Segredo certo, guardado | 200 `{"success": true, "message": null}` | contrato da operadora |
| Segredo errado | 404 | não confirma o endereço (310 FR-027a) |
| Corpo > 64 KB | 413 | igual à rota de hoje |
| Mais de 60/min do mesmo cliente | 429 | igual ao `@limiter.limit` de hoje |
| Banco fora / falha ao guardar | **400** | a InfinitePay só reenvia com 400 (310 R2); aqui reenviar conserta |
| Outro método / outro caminho | 405 / 404 | — |

A rota de hoje responde 200 mesmo quando `registrar_aviso` falha ("nunca devolver 500 à
operadora"). No receptor, a falha de gravação é exatamente o caso em que o reenvio ajuda.

## R5 — Relógio e segredo anterior

`infinitepay_webhook_token_anterior_ate` é gravado em relógio de São Paulo ingênuo (`now_sp()`,
`ZoneInfo("America/Sao_Paulo")`). O receptor compara com `datetime.now(ZoneInfo("America/Sao_Paulo"))
.replace(tzinfo=None)` — a mesma expressão de `app/constants.py:now_sp`. Comparação do segredo com
`hmac.compare_digest`. `received_at` da caixa também em São Paulo (armadilha 2 do `docs/00` §6: as
`virtual_*` usam um relógio só).

## R6 — IP do cliente e limites

O Render acrescenta o IP do cliente ao **fim** do `X-Forwarded-For` (`frontend/server.js`,
`ipDoCliente`, provado na 310). O receptor usa o último item, senão `REMOTE_ADDR`. Limite de 60/min
por IP em memória (um processo, `--workers 1`). Teto global de **120 recusas guardadas por hora**
(em memória): acima disso o segredo errado responde 404 sem gravar — sem o teto, quem troca o
`X-Forwarded-For` a cada chamada encheria a tabela. 120/h cobre com folga a troca de segredo com
links abertos (a operadora não reenvia com 404).

## R7 — Dreno no backend

**Reivindicação por arrendamento, não por trava de linha.** `registrar_aviso` e `processar_aviso`
fazem `commit` — uma trava `FOR UPDATE` cairia no primeiro commit. O dreno marca `claimed_at` num
`UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED) RETURNING id` (dois processos nunca pegam a
mesma linha) e uma linha com `claimed_at` de mais de 5 min volta a ser elegível (processo morto no
deploy) — o mesmo critério de `_reivindicar_aviso`.

**Ordem por linha**: `registrar_aviso` → marca `drained_at`/`notification_id` (commit) →
`processar_aviso`. Registrado, o aviso já está na fila da 310: se `processar_aviso` falhar, a
`reprocessar_avisos` da varredura retoma. A caixa só responde pelo trecho "chegou → registrado".

**Onde roda**: (a) primeira rotina de `ciclo_de_varredura()`, antes de `expirar_reservas` — senão
uma reserva vencida seria liberada com o pagamento esperando na caixa; (b) thread
`_start_caixa_de_avisos` a cada `VIRTUAL_CAIXA_INTERVAL` = 10 s (o aviso de hoje é processado na
hora; 60 s da varredura seria regressão para quem não volta pelo "Continuar").

**Linha parada**: `drained_at IS NULL` e `received_at` há mais de 1 h e `alerted_at IS NULL` →
`_avisar_a_conferir("virtual.caixa:<id>", …)` e grava `alerted_at`.

## R8 — Endereço do aviso nos links novos

Constante `AVISOS_BASE_URL = "https://manto-avisos.onrender.com"` em `app/config.py`, ao lado de
`PLATFORM_BASE_URL`; `Config.INFINITEPAY_AVISO_BASE_URL = _url_para_fora(os.getenv(...),
AVISOS_BASE_URL, ..., permitir_local=MAIL_SUPPRESS_SEND)` (Princípio XIV). `virtuais_ops.py:1081`
passa a usar essa base só para o `webhook_url`; o `redirect_url` segue em `PUBLIC_BASE_URL`.

O Render não documenta o que faz se o nome `manto-avisos` já existir globalmente no
`onrender.com`. Mitigação: a loja está desligada (interruptor da 310) — nenhum link é criado entre
o deploy e a conferência da URL no painel; se vier outra, a constante muda antes de ligar a loja
(quickstart §2).

## R9 — `render.yaml`

- `buildFilter` existe no Blueprint, com glob, "always relative to the repo's root directory";
  forma `buildFilter: {paths: [...], ignoredPaths: [...]}`. Mudança no próprio `render.yaml` é
  processada sempre.
- `rootDir` já filtra: "Render only triggers an autodeploy if your changes affect files anywhere
  under that directory." O `manto-frontend` (`rootDir: frontend`) e o `manto-avisos`
  (`rootDir: servicos/avisos`) não precisam de filtro. A dívida 22 do `docs/05` ("todo push
  rebuilda os dois serviços") vale só para o backend (`rootDir: .`) — corrigir o registro.
- Healthcheck: 2xx ou 3xx é saudável, resposta em até 5 s, o deploy espera até 15 min e, se falhar,
  "continues routing traffic to your service's existing instances".
- Serviço novo num Blueprint com sincronização automática é criado no push ("triggers a deploy of
  any added or modified resources").
- Plano: `starter` (0,5 CPU, 512 MB). O `free` "spins down … after 15 minutes" e leva ~1 min para
  acordar — perderia o aviso. O workspace Pro não inclui máquina.

## R10 — Retorno da família

TanStack Query já tem `retry`/`retryDelay` em `useMutation`: a mutação guarda as variáveis (os
identificadores) entre tentativas — nada a guardar à mão depois de limpar a URL. Repete quando o
erro não é `ApiRequestError` (rede) ou é `status >= 500`; para em 2xx/4xx. Atrasos 5 s, 20 s,
60 s. A página continua em "Confirmando…" durante as tentativas (o `finally` só roda no fim).

## R11 — Constituição

A seção Operação e Deploy diz "cada deploy abre ~1 min de 502 na porta pública (o frontend não tem
healthcheck)". Com esta feature isso deixa de ser verdade para frontend e avisos: emenda MINOR
3.2.0 (Princípio VII: mudança de infraestrutura entra no mesmo ciclo), aprovada pelo dono junto do
plano em 10/11.
