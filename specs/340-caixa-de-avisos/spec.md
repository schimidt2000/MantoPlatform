<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Feature 340 — O pagamento da loja não se perde num push: o aviso espera numa caixa fora do deploy

**Branch**: `340-caixa-de-avisos` (da `main` em `96837811`, worktree `C:\tmp\mp340`) · **Created**:
2026-11-10 · **Status**: Rascunho · **Migration**: aditiva (tabela nova `virtual_payment_inbox`) ·
**Nível**: 1 (feature) — serviço novo no Render, tabela nova, dois domínios (loja virtual e
infraestrutura de deploy); constituição, Princípio VI

**Input**: pedido do dono (09–10/11/2026): "eu aparentemente não vou poder fazer pushes durante o
período do dia, porque pode ser fechado algum evento e ter um pagamento no meio do caminho que pode
rolar algum bug. Tem alguma forma da gente se prevenir contra isso?" → "Não seria uma saída também um
outro serviço no render rodando (24/7), onde não é afetado pelos pushes?" → "De fato acho que vale
guardar essa ideia para janeiro" (tirar o disco do backend) → workspace do Render é Pro → "Pode
implementar". Plano aprovado: `C:\Users\schim\.claude\plans\proud-waddling-peach.md`.

## O pedido, nas palavras do dono *(obrigatório)*

"Eu aparentemente não vou poder fazer pushes durante o período do dia, porque pode ser fechado algum
evento e ter um pagamento no meio do caminho que pode rolar algum bug."

**O sintoma, como ele existe hoje.** A regra R-20 da 310 proíbe deploy entre 9h e 23h de 1º/11 a
25/12. Cada push troca os dois serviços web: o `manto-frontend` não tem healthcheck e o
`manto-backend` tem disco persistente — e, pela documentação do Render, "Adding a disk to a service
prevents zero-downtime deploys". São ~60 s de 502 na porta pública. O aviso de pagamento da
InfinitePay entra por `app.mantoproducoes.com.br/api/webhooks/infinitepay/<token>` (frontend →
backend) e a operadora **só reenvia com 400** (`specs/310-…/research.md` R2): um 502 perde o aviso.
A segunda prova, o retorno da família pelo "Continuar", é enviada uma vez só e o erro é engolido
(`PedidoVirtualPage.tsx`, `useRetornoDoCheckout`). Sem nenhuma das duas, a venda paga vira trabalho
manual em "Pagamentos a conferir", com uma família esperando o link do Papai Noel.

**A decisão.** Agora: um serviço pequeno e separado, `manto-avisos`, que só **recebe e guarda** o
aviso; quem decide continua sendo o backend, pela mesma regra de hoje (padrão de mercado *webhook
inbox*). Junto, os ajustes baratos do `render.yaml` que tiram do caminho os pushes que não mexem no
backend. Em janeiro: tirar o disco do backend (deploy sem queda para tudo) — fora desta feature.

## Cenários e Verificação *(obrigatório)*

### História 1 — Pagamento feito durante um deploy vira venda sozinho (Prioridade: P1)

A família paga o Pix no minuto em que o backend está trocando de container. O aviso da operadora
chega ao `manto-avisos`, que está no ar, e fica guardado. Quando o backend volta, ele pega o aviso
guardado e decide pela mesma regra de sempre: venda, sala do Meet e e-mail de compra confirmada.
Ninguém da equipe precisa fazer nada, e o dono pode dar push de backend de dia sem medo de perder
pagamento.

**Por que esta prioridade**: é o pedido inteiro. Sem ela, a R-20 continua valendo.

**Verificação**: cenários 1, 2 e 13–17 do `verify_340.py` — o receptor guarda com o backend fora; o
dreno transforma o aviso guardado em venda com a mesma regra da 310 (`registrar_aviso` →
`processar_aviso`), contra `manto_340`.

**Cenários de aceite**:

1. **Dado** um pedido aguardando pagamento e o backend fora do ar, **Quando** a InfinitePay manda o
   aviso com o segredo certo, **Então** o receptor responde 200 e o aviso fica guardado na caixa.
2. **Dado** um aviso guardado na caixa, **Quando** o backend volta e drena a caixa, **Então** o
   pedido vira venda exatamente como viraria pelo aviso direto (mesmo desfecho, mesmo evento, mesmo
   e-mail), e a linha da caixa fica marcada como drenada.
3. **Dado** um aviso guardado e uma reserva cuja trava venceu, **Quando** a varredura roda, **Então**
   a caixa é drenada **antes** da expiração de reservas — o pagamento não perde o horário para a
   varredura.
4. **Dado** o mesmo aviso entregue duas vezes à caixa, **Quando** os dois são drenados, **Então** só
   uma venda existe (o segundo cai como duplicado pela regra que já existe).
5. **Dado** dois processos do backend drenando ao mesmo tempo, **Quando** há uma linha na caixa,
   **Então** só um deles a processa.

---

### História 2 — Com o backend no ar, o aviso continua sendo decidido em segundos (Prioridade: P1)

No dia a dia, sem deploy, o caminho novo não pode deixar a família esperando mais do que hoje: o
aviso guardado é drenado em até ~10 s e a venda sai na hora.

**Por que esta prioridade**: trocar o endereço do aviso não pode piorar o caso normal.

**Verificação**: cenário 9 do `verify_340.py` — a thread de dreno é registrada com intervalo de
10 s e respeita `MANTO_SEM_THREADS`; o `webhook_url` dos links novos aponta para o receptor.

**Cenários de aceite**:

1. **Dado** o backend no ar, **Quando** um aviso entra na caixa, **Então** ele é decidido na próxima
   volta do dreno (no máximo ~10 s), sem esperar a varredura de 60 s.
2. **Dado** um link de pagamento criado depois desta feature, **Quando** se lê o endereço de aviso
   que foi para a operadora, **Então** ele aponta para o `manto-avisos`.
3. **Dado** um link criado antes desta feature (endereço antigo), **Quando** a operadora avisa pelo
   endereço antigo, **Então** a rota antiga do backend continua recebendo como hoje.

---

### História 3 — O receptor só guarda o que é da operadora, e nunca expõe o segredo (Prioridade: P1)

O `manto-avisos` é um endereço público. Ele tem de recusar quem não tem o segredo sem confirmar que o
endereço existe, não pode ser usado para encher o banco e não pode deixar o segredo em log.

**Por que esta prioridade**: um receptor novo de dinheiro não pode abrir uma porta que a 310 fechou.

**Verificação**: cenários 3–8 e 10 do `verify_340.py` — segredo errado (404, **deve falhar**),
segredo anterior dentro e fora da janela, corpo grande, corpo sem tamanho declarado, teto de
recusas, segredo fora do log.

**Cenários de aceite**:

1. **Dado** um segredo errado, **Quando** alguém chama o receptor, **Então** a resposta é 404 e nada
   entra como aviso válido.
2. **Dado** o segredo anterior dentro das 24 h de troca, **Quando** a operadora avisa por ele,
   **Então** o aviso é aceito; vencida a janela, é recusado (404).
3. **Dado** um corpo acima de 64 KB (declarado ou não), **Quando** chega ao receptor, **Então** a
   resposta é 413 e nada é guardado.
4. **Dado** o banco indisponível, **Quando** o aviso chega, **Então** o receptor responde 400 para a
   operadora reenviar — nunca 200 sem ter guardado.
5. **Dado** qualquer chamada, **Quando** se lê o log do receptor, **Então** o segredo do endereço não
   aparece.

---

### História 4 — A família que volta do pagamento durante a troca é atendida (Prioridade: P2)

A família paga, toca em "Continuar" e cai na página do pedido no minuto em que o backend troca de
container. Hoje a página manda os identificadores uma vez só e, se der erro, desiste em silêncio. Com
a feature, ela tenta de novo algumas vezes e a família vê a confirmação assim que o backend volta.

**Por que esta prioridade**: o aviso guardado (História 1) já garante a venda; esta história garante
que a família não fique olhando "Confirmando…" sem resposta.

**Verificação**: conferência de tela em 375×812 com o backend derrubado e levantado de novo (o envio
do retorno se repete e a página mostra a confirmação), e `npm run typecheck`.

**Cenários de aceite**:

1. **Dado** o backend fora do ar, **Quando** a família volta do checkout, **Então** a página tenta
   de novo em 5 s, 20 s e 60 s, sem que a família faça nada.
2. **Dado** o backend de volta, **Quando** a tentativa seguinte passa, **Então** a página mostra o
   pedido confirmado como hoje.
3. **Dado** uma resposta 4xx do retorno, **Quando** ela chega, **Então** a página não repete (o
   servidor respondeu e decidiu).

---

### História 5 — Push que não mexe no backend não derruba nada (Prioridade: P2)

Push só de documentação ou de especificação não reinicia serviço nenhum. Push só de tela troca o
frontend sem queda. O `manto-avisos` só faz deploy quando a pasta dele muda.

**Por que esta prioridade**: hoje até o commit de "novidades" derruba a produção por um minuto.

**Verificação**: cenário 11 do `verify_340.py` (leitura do `render.yaml`: healthcheck do frontend,
filtro de caminhos do backend, serviço novo com `rootDir` próprio e sem disco) e conferência nos
Events do Render no primeiro deploy (quickstart).

**Cenários de aceite**:

1. **Dado** um push que só altera `docs/` ou `specs/`, **Quando** chega à `main`, **Então** o
   `manto-backend` não reinicia.
2. **Dado** um push que só altera `frontend/`, **Quando** chega à `main`, **Então** o
   `manto-frontend` sobe o container novo e só troca depois de o healthcheck responder.
3. **Dado** um push que não altera `servicos/avisos/`, **Quando** chega à `main`, **Então** o
   `manto-avisos` não reinicia.

---

### História 6 — A equipe fica sabendo se um aviso empacar na caixa (Prioridade: P3)

Se o backend não conseguir drenar uma linha (erro repetido), ela não pode ficar esquecida: com mais
de 1 h parada, o sino avisa o Comercial e o Superadmin, do mesmo jeito que avisa um aviso sem
desfecho hoje.

**Por que esta prioridade**: rede de segurança; o caso normal nunca passa de segundos.

**Verificação**: cenário 12 do `verify_340.py`.

**Cenários de aceite**:

1. **Dado** uma linha da caixa sem dreno há mais de 1 h, **Quando** o dreno roda, **Então** o sino
   `virtual.atencao` é tocado uma vez para essa linha (deduplicado).

### Casos de borda

- **Retorno forjado antes do aviso**: a regra de `registrar_aviso` (o aviso autenticado sobrescreve
  o registro que veio do retorno) vale igual pelo caminho da caixa, porque o dreno chama a mesma
  função.
- **Segredo trocado entre a chegada e o dreno**: a validade do segredo é decidida **na chegada**; a
  caixa guarda só o resultado (`secret_ok`), nunca o segredo.
- **Aviso guardado de pedido inexistente** (órfão): mesmo desfecho de hoje (`orfao`), via
  `processar_aviso`.
- **Corpo que não é JSON**: guardado como veio (é o aviso da operadora); o dreno trata como payload
  vazio, como a rota de hoje.
- **Enxurrada de chamadas com segredo errado**: teto global de recusas guardadas por hora; acima
  dele, 404 sem gravar.
- **Receptor reiniciando** (deploy da própria pasta): sem disco e com healthcheck, o Render só troca
  depois de o novo responder.
- **`manto-avisos` fora do ar** (falha do Render): a operadora recebe erro e o aviso pode se perder —
  o mesmo risco de hoje, só que num serviço que quase nunca reinicia. A varredura e "Pagamentos a
  conferir" seguem como rede.
- **Comando no Shell com `MANTO_SEM_THREADS=1`**: a thread de dreno não sobe.
- **Primeiro deploy, receptor no ar antes da migration do backend**: a gravação falha (tabela ainda
  não existe) e o receptor responde 400 — a operadora reenvia. No primeiro deploy a loja está
  desligada, então nenhum aviso real é esperado nessa janela.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Receptor (`manto-avisos`)**

- **FR-001**: Um serviço web separado DEVE receber `POST /api/webhooks/infinitepay/<token>` (o mesmo
  caminho de hoje: a troca é só de host) e responder em menos de 1 s.
- **FR-002**: O receptor DEVE conferir o segredo contra `site_settings` com o mesmo critério de
  `virtuais_ops.token_do_aviso_valido`: o atual, ou o anterior enquanto
  `infinitepay_webhook_token_anterior_ate` (relógio de São Paulo, ingênuo) não passou; comparação em
  tempo constante; segredo vazio (no banco ou na URL) nunca vale.
- **FR-003**: Segredo certo → guarda o corpo como veio numa linha da caixa (`secret_ok = true`) e
  responde **200** `{"success": true, "message": null}`.
- **FR-004**: Segredo errado → guarda um resumo de até 2 KB com `secret_ok = false` (até 120 por
  hora no total; acima disso, não guarda) e responde **404** — 404, não 403, para não confirmar o
  endereço (310 FR-027a).
- **FR-005**: Corpo acima de 64 KB, com ou sem `Content-Length`, → **413**, nada guardado.
- **FR-006**: Falha ao conferir o segredo ou ao guardar (banco fora) → **400**, para a operadora
  reenviar. O corpo de toda resposta de erro do receptor é fixo (contrato), sem detalhe interno.
- **FR-007**: No máximo 60 chamadas por minuto por cliente; acima → 429.
- **FR-008**: O segredo do endereço NUNCA vai para log nem para o banco (a caixa guarda o corpo e o
  resultado da conferência, não o token).
- **FR-009**: `GET /health` responde 200 se o processo está vivo (sem tocar o banco, para um soluço
  do Postgres não fazer o Render reiniciar o serviço); `GET /health/banco` responde 200 só se o banco
  responde (para a sondagem).
- **FR-010**: O receptor NÃO decide nada nem importa o código do backend: não reconsulta a
  operadora, não cria evento, não manda e-mail.

**Backend**

- **FR-011**: O backend DEVE drenar a caixa reivindicando linhas por `FOR UPDATE SKIP LOCKED` (dois
  processos nunca pegam a mesma linha) e, para cada uma: `secret_ok` → `registrar_aviso(payload)` e,
  se devolver um id, `processar_aviso(id)`; `secret_ok = false` → `registrar_aviso_invalido(payload)`.
  As três funções existentes NÃO mudam.
- **FR-012**: A caixa responde só pelo trecho "chegou → registrado na fila da 310": registrado o
  aviso, a linha fica marcada (`drained_at`, `notification_id`) **antes** da decisão; se
  `processar_aviso` falhar depois disso, quem retoma é a `reprocessar_avisos` da varredura (310). Falha
  no registro mantém a linha na caixa com `attempts`/`error`, e ela volta na próxima volta.
- **FR-013**: O dreno DEVE ser a **primeira** rotina de `ciclo_de_varredura()`, antes de
  `expirar_reservas`.
- **FR-014**: O backend DEVE ter uma thread de dreno com intervalo de 10 s, iniciada junto das outras
  e desligada por `MANTO_SEM_THREADS=1`.
- **FR-015**: Linha não drenada há mais de 1 h → sino `virtual.atencao` uma vez por linha
  (deduplicado pela chave do sino), no molde de `_avisar_a_conferir`.
- **FR-016**: O endereço de aviso dos links novos DEVE vir de uma configuração com default real em
  `app/config.py` apontando para o `manto-avisos`, montada por `_url_para_fora` (Princípio XIV);
  a rota antiga `/api/webhooks/infinitepay/<token>` do backend continua registrada e funcionando.
  Saída sem deploy de código: a env `INFINITEPAY_AVISO_BASE_URL` apontada para
  `https://app.mantoproducoes.com.br` devolve os links novos à rota antiga.

**Página da família**

- **FR-017**: O envio do retorno do checkout DEVE repetir até 3 vezes (5 s, 20 s, 60 s) quando a
  resposta for erro de rede ou 5xx; com resposta 2xx ou 4xx, para. Os identificadores ficam em
  memória depois de a URL ser limpa.

**Deploy (`render.yaml`, cada item em commit isolado)**

- **FR-018**: Serviço `manto-avisos`: plano pago sempre ligado (o gratuito dorme após 15 min e
  perderia o aviso), `rootDir` na pasta do receptor, `healthCheckPath: /health`, sem disco,
  `DATABASE_URL` do `manto-postgres`.
- **FR-019**: `manto-frontend` ganha `healthCheckPath` (dívida 22 do `docs/05`).
- **FR-020**: `manto-backend` ganha filtro de caminhos que ignora `docs/`, `specs/`, `frontend/`, a
  pasta do receptor, `.claude/` e `.specify/`.
- **FR-021**: A regra R-20 (sem deploy 9h–23h na campanha) é substituída em `DEVELOPMENT.md`, na
  skill `manto-deploy` e na constituição (seção Operação e Deploy, emenda MINOR): push de backend
  segue "de preferência a partir das 19h" pela equipe, sem proibição por pagamento; migration e
  `startCommand` continuam à noite; depois de cada deploy, conferir "Pagamentos a conferir". A sonda
  de produção do `manto-deploy` passa a incluir `GET /health/banco` do `manto-avisos`.

### Entidades *(se houver dados)*

- **VirtualPaymentInbox** (`virtual_payment_inbox`): o aviso como chegou ao receptor, antes de
  qualquer decisão. Atributos: `id`, `received_at` (relógio de São Paulo, como as demais `virtual_*`),
  `body` (texto, até 64 KB; 2 KB quando `secret_ok = false`), `secret_ok`, `drained_at`,
  `notification_id` (→ `virtual_payment_notifications.id`, nulo até drenar ou quando o registro foi
  descartado como já decidido), `attempts`, `error`, `alerted_at`. Índice parcial nas linhas não
  drenadas. Modelo em `app/models.py`, migration à mão, aditiva.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `POST /api/webhooks/infinitepay/<token>` no `manto-avisos` — **público, protegido pelo segredo do
  endereço** (mesma regra da rota da 310); sem sessão. Linha na tabela de `docs/01` §4.3.
- `GET /health`, `GET /health/banco` no `manto-avisos` — públicos, sem dado.
- Nenhum endpoint novo no backend; o dreno é rotina de fundo.

## Verificação (`verify_340.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/340-caixa-de-avisos/verify_340.py`, contra **`manto_340`** (o `manto_local` está na
migration do CRM 334, sem push; banco próprio do dump de 10/11 — exceção ao Princípio VIII registrada
no `plan.md`), com `DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development`,
`MANTO_SEM_THREADS=1`. O receptor é exercitado como aplicação WSGI pelo cliente de teste do
Werkzeug; InfinitePay e Google por dublê (trava `INFINITEPAY_SUPPRESS_CALLS`). Escrita conferida
por conexão separada; limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Aviso com segredo atual | 200 em menos de 1 s + linha na caixa com o corpo como veio, `secret_ok` | não |
| 2 | Banco fora (URL inválida no receptor) | 400, não 200 | não |
| 3 | Segredo errado | **404** e linha recusada de 2 KB | **sim** |
| 4 | Segredo anterior dentro / fora da janela | 200 / 404 | não / **sim** |
| 5 | Corpo 64 KB + 1 com e sem `Content-Length` | 413, nada guardado | não |
| 6 | 61ª chamada no mesmo minuto | 429 | não |
| 7 | Teto de recusas por hora | acima do teto, 404 sem gravar | não |
| 8 | Log do receptor | o segredo não aparece | não |
| 9 | Thread de dreno e `webhook_url` | `_start_caixa_de_avisos` chamada dentro do bloco que `MANTO_SEM_THREADS=1` desliga (conferência no código, **nunca** subindo `create_app()` sem a trava — subiria Google e e-mail reais) e uma volta do laço drena; intervalo 10 s; link novo aponta para o receptor; rota antiga segue registrada | não |
| 10 | `/health` e `/health/banco` | 200 / 200 com banco, 503 sem banco | não |
| 11 | `render.yaml` | serviço novo com `rootDir`, healthcheck e sem disco, e `startCommand` aceito pelo parser real do gunicorn (o `validar_startcommand.py` só lê o backend); healthcheck no frontend; filtro no backend | não |
| 12 | Linha parada > 1 h | sino `virtual.atencao` uma vez | não |
| 13 | Dreno de aviso pago | venda pela mesma regra (desfecho, evento, e-mail por dublê); linha drenada com `notification_id` | não |
| 14 | Mesmo aviso duas vezes | uma venda, o segundo duplicado | não |
| 15 | Dois drenos concorrentes (duas conexões, barreira) | uma linha processada uma vez | não |
| 16 | Ordem no ciclo | caixa drenada antes de `expirar_reservas` (pagamento não perde o horário) | não |
| 17 | Retorno forjado antes do aviso, via caixa | o aviso autenticado manda | não |
| 18 | limpeza | pedidos, avisos, linhas da caixa, sinos e eventos descartáveis apagados | — |

Regressão: `verify_310.py`, `verify_205.py`, `verify_304.py` contra `manto_340`.

Conferência de tela: `/catalogo/v/pedido/<token>?order_nsu=…` em 375×812 com o backend local
derrubado e levantado (o retorno repete e a confirmação aparece).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Um pagamento feito durante um deploy do backend vira venda sem ação da equipe, em até
  ~1 min depois de o backend voltar.
- **SC-002**: Sem deploy, a venda de um aviso que chega pelo caminho novo sai em até ~10 s (não pior
  do que hoje para quem não volta pelo "Continuar").
- **SC-003**: Push só de documentação não derruba nenhum serviço; push só de tela não gera 502.
- **SC-004**: Nenhum pagamento da campanha de Natal termina em "a conferir" por causa de um deploy.
- **SC-005**: A proibição de deploy 9h–23h deixa de existir; o dono publica backend de dia sem risco
  para pagamento (resta só o ~1 min de queda para a equipe até janeiro).

## Fora de escopo

- Tirar o disco do `manto-backend` (uploads para armazenamento externo) — janeiro, registrado no
  `docs/05`.
- Preview environments / staging (o workspace Pro já permite) — janeiro, junto do disco.
- Avisos da ClickSign (317) e do Inter (318): a ClickSign tem conferência periódica e o Inter é lido
  da caixa de e-mail; nenhum dos dois perde dado num 502.
- Mudar `registrar_aviso`, `processar_aviso`, `decidir_pagamento` ou qualquer regra da 310.
- Desligar a rota antiga do aviso no backend.
- Limpeza periódica da caixa: o volume é o de `virtual_payment_notifications` (dezenas por dia),
  que também não é limpa.
- Domínio próprio (`avisos.mantoproducoes.com.br`) para o receptor: o endereço só é lido pela
  operadora; o do Render basta.

## Docs a atualizar

`docs/00` §2 (topologia: quarto serviço) e §6 se surgir armadilha; `docs/01` §2.10 (tabela nova),
§4.3 (rota do receptor) e §5 (`render.yaml`, deploy, sondagem); `docs/02` (página do pedido:
retentativa do retorno); `docs/03` (entrada no topo + índice + linha da Loja de Interações
Virtuais); `docs/04` §Loja Virtual (o aviso entra pela caixa); `docs/05` (quitar a dívida 22,
registrar "tirar o disco do backend — janeiro"); `DEVELOPMENT.md` (§Publicar, §Operar, R-20); skill
`manto-deploy`; constituição (Operação e Deploy, v3.2.0); `CLAUDE.md` §2 (topologia e regra de
horário).

## Premissas

- A InfinitePay reenvia o aviso quando recebe 400 (`specs/310-…/research.md` R2); não depende disso
  para o caminho feliz.
- O endereço do receptor é o que o Render der ao serviço `manto-avisos`
  (`https://manto-avisos.onrender.com` se o nome estiver livre). Se vier outro, a constante muda
  **antes** de ligar a loja; a loja está desligada hoje (interruptor da 310), então nenhum link é
  criado entre o deploy e essa conferência.
- O receptor usa o mesmo Postgres (`manto-postgres`), por conexão curta por chamada; o volume é de
  dezenas de avisos por dia. Ele recebe a mesma credencial do backend (o Postgres gerenciado do
  Render tem um usuário só pelo Blueprint); o código do receptor só lê `site_settings` e só escreve
  em `virtual_payment_inbox`, e isso é o que a revisão confere.
- Custo: instância `starter` cobrada por uso (o plano Pro do workspace não inclui máquina); aprovado
  pelo dono em 10/11.
- O backend continua com ~1 min de queda por deploy até janeiro; a equipe segue preferindo publicar a
  partir das 19h.
