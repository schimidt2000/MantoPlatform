# Pesquisa (Phase 0) — 310 Pagamento da loja virtual

Base: `98192e8`. Evidência: `pesquisa/` (auditoria, operadoras, refutação) e o teste 0/A em produção
(spec, seção "Teste 0"). Cada decisão abaixo responde a um FR da spec.

## R1 — Uma decisão só para "este pagamento vira venda?" (FR-001–FR-005, FR-007, FR-008, FR-015, FR-017)

**Decisão**: nova função `decidir_pagamento(order_id, consulta, *, identificadores, origem)` em
`virtuais_ops.py`, chamada pelo aviso, pelo retorno, pela varredura e pelo reprocessamento de avisos.
Ela é a ÚNICA que chama `efetivar_pedido` e `_abrir_devolucao`. Passos, numa transação:

1. `SELECT … FROM virtual_orders WHERE id=:id FOR UPDATE` com `populate_existing` — relê o status.
2. **Ordem fixa de travas** em toda a feature: pedido → horário → campanha. Hoje `_liberar_reserva`
   trava só o horário e escreve no pedido; passa a travar o pedido primeiro (sem isso, duas rotinas
   que travam em ordens diferentes podem se esperar para sempre).
3. `_pagamento_confere(order, consulta)`: `paid is True` **e** `paid_amount` presente **e**
   `paid_amount >= total_value`. Nunca `paid_amount or amount` (zero cairia no nominal do link).
   Não confere → desfecho `divergente` (alerta, sem venda, sem devolução automática: a equipe confere).
4. Estado do pedido:
   - `pago` com os mesmos identificadores → `duplicado` (nada a fazer);
   - `pago` com **outra** cobrança (transaction_nsu/slug diferentes dos gravados) → devolução da
     segunda cobrança, motivo `pagamento_em_dobro`, pedido segue pago (FR-014);
   - `cancelado` → devolução, motivo `pagamento_sem_pedido_ativo` (pagou depois de cancelado);
   - `reservado`/`aguardando`/`expirado` → segue.
5. Horário (ao vivo), travado `FOR UPDATE`: **tomado** se `order_id` não é nulo e ≠ este pedido, ou
   se `status == vendido` e `order_id` ≠ este pedido (inclusive nulo, para cobrir vendas antigas sem
   dono gravado). Tomado → devolução `conflito_horario` (ou `conflito_sem_confirmacao` se o pedido foi
   liberado sem prova).
6. Folga: `start_at <= agora() + VIRTUAL_MIN_MINUTOS_NO_PAGAMENTO` (30 min) → devolução
   `horario_passou`. **Não** é a antecedência de 2 h: essa vale para **reservar** (R9). Um pedido feito
   2h01 antes e pago 15 min depois precisa virar venda; recusar por "menos de 2 h" puniria quem
   cumpriu a regra.
7. Gravado: trava a campanha; `recorded_sold >= recorded_capacity` → devolução `sem_vaga_de_video`.
8. Efetiva **no banco primeiro**: pedido `pago`, horário `vendido` com `order_id = order.id`,
   `CalendarEvent` com id local `virtual-local-<nsu>` e `meet_pending=True`, entrega, presente 3D,
   identificadores e recibo gravados — commit. Só **depois**, fora das travas, chama o Google
   (`regerar_sala`, caminho do id local que já existe) e o e-mail. Falha do Google → a varredura de
   salas retenta (R11). Isso elimina o evento órfão do perdedor de uma disputa (FR-005), porque a
   disputa é decidida no banco antes de qualquer chamada externa.

**Por quê**: a refutação mostrou que a regra hoje existe em pedaços (dono do horário e valor só no
aviso; nada na varredura) e decide sobre leitura velha. Uma função com trava do pedido resolve as 6
variantes de venda dupla e o "pago que volta a expirado" de uma vez.

**Alternativas**: (a) só copiar as checagens do aviso para a varredura — mantém duas cópias que
divergem de novo; (b) `SERIALIZABLE` na transação — o Postgres resolveria a corrida, mas com retry de
serialização espalhado em código que faz HTTP; rejeitado.

## R2 — Aviso de pagamento: responder rápido, processar fora da requisição (FR-013, FR-016, FR-029)

**Decisão**: a rota grava o aviso (`VirtualPaymentNotification`, estado `pendente`) e responde **200**
em milissegundos. O processamento roda numa thread curta disparada na hora (com `app_context`) e, como
rede de segurança, a varredura reprocessa avisos `pendente`/`retido` (inclusive de pedidos expirados ou
cancelados) com o mesmo contador de tentativas da política existente, por até 48 h; esgotou → vira
"a conferir" (R10).

- **Idempotência**: `transaction_nsu` continua UNIQUE, mas a reentrega de um aviso cujo registro não
  tem desfecho **final** (`efetivado`, `conflito`, `devolucao_aberta`, `duplicado`, `divergente`,
  `orfao`) é reprocessada em vez de virar "duplicado".
- **Sem token**: grava `transaction_nsu = NULL`, `raw_payload` cortado em 2 KB e 404 — não ocupa a
  chave de um aviso legítimo. Rota ganha `@limiter.limit("60 per minute")` e recusa corpo > 64 KB.
- **Identificadores do corpo** só vão para o pedido depois de a reconsulta **com eles** provar o
  pagamento (FR-017): a reconsulta usa os identificadores **deste** aviso.
- `compare_digest` no token.

**Por quê**: a InfinitePay pede resposta em < 1 s e só reenvia com 400; hoje o processamento faz
payment_check + Google + SMTP dentro da requisição, segurando a trava do horário durante HTTP.

**Alternativas**: fila externa (Redis/RQ) — infraestrutura nova no Render; a varredura já é uma fila
com claim atômico. Responder 400 quando "retido" para a operadora reenviar — a política de reenvio dela
não é publicada; preferimos não depender dela.

## R3 — Retorno do checkout como segunda prova (FR-010, FR-011)

**Decisão**: `POST /api/virtuais/pedidos/<public_token>/retorno` com `order_nsu, slug,
transaction_nsu, capture_method, receipt_url` (o que a InfinitePay põe na URL de retorno). O servidor:
confere `order_nsu` == o do token (senão 404 sem gravar); reconsulta com esses identificadores; chama
`decidir_pagamento`. A `PedidoVirtualPage` lê a query uma vez, faz o POST, e limpa a URL
(`history.replaceState`) para o link compartilhado não carregar identificadores.

**Por quê**: o teste 0 provou que `payment_check` só com `handle + order_nsu` responde
`200 {"success":false}` — sem os identificadores do aviso ou do retorno não há como provar. O retorno
existe sempre que a família toca "Continuar".

## R4 — Semântica da reconsulta (FR-011)

**Decisão**: `consultar_pagamento` devolve um de quatro resultados, não mais `dict` cru:
`pago` (`success` e `paid` verdadeiros, com valores), `nao_pago` (`success` e `paid=false`),
`nao_encontrado` (`success:false`, ou 404 "Not found"), `nao_sei` (timeout, 5xx, corpo ilegível, trava
local). Regras:

- **com** identificadores (aviso/retorno): `nao_encontrado` = cobrança não paga com esses dados →
  aviso fica `pendente` e é retentado (pode ser atraso de propagação);
- **sem** identificadores (varredura de pedido que nunca recebeu aviso nem retorno): `nao_encontrado`
  é o caso normal de quem abandonou o checkout → libera como hoje (`expirado`), **numa** consulta, sem
  gastar as 3 tentativas; `expired_unverified` só quando o resultado for `nao_sei`.
- 4xx ao **criar o link** (`external_checkout_not_enabled`, campo inválido) é `recusado` com o código
  da operadora preservado e **não** é repetido.

**Por quê**: hoje 4xx com JSON vira `Recusou`, corpo sem `paid` vira `Indisponivel`, e os dois retêm 3
ciclos e liberam "sem prova" — foi o que o teste 0 mostrou com o pedido 3.

## R5 — Trava fora da produção (FR-020; constituição XIV)

**Decisão**: `_suppress_infinitepay()` em `app/config.py` no molde de `_suppress_calendar_event_writes`
(`INFINITEPAY_SUPPRESS_CALLS=true` trava em qualquer ambiente; `INFINITEPAY_ALLOW_LOCAL_CALLS=true`
libera o local; banco localhost/127.0.0.1/sqlite = travado). Config `INFINITEPAY_SUPPRESS_CALLS`.
`infinitepay_client._post` lê `current_app.config` **a cada chamada** (chave ausente = travado) e,
travado, levanta `InfinitePayTravada` (subclasse de `InfinitePayIndisponivel` → "não sei"). A reserva
traduz para "O pagamento está travado neste ambiente (cópia de teste)". A criação de evento de venda
virtual no Google respeita `CALENDAR_SUPPRESS_EVENT_WRITES` (já existe; o docstring passa a citar a
loja). O cliente fica sem `import flask` no topo: lê a config por parâmetro injetado pela camada
`_ops`, para continuar testável sem app (Princípio III).

## R6 — Interruptor e publicação (FR-021, FR-022)

**Decisão**: coluna `site_settings.virtuais_pagamento_ativo` (bool, default **false**). Checada só em
`_gerar_link_pagamento`. Aviso, retorno e reconsulta ignoram o interruptor (pedido aberto precisa
fechar). `_campos_faltantes_para_publicar` recusa sem handle, sem token ou com o interruptor desligado.
Na produção, depois do deploy, o dono liga no card (passo do quickstart) — a tag e o token já existem
desde o teste 0.

## R7 — Tela de configurações (FR-023–FR-026)

- `update_settings` aplica `email_notifications_enabled`, `whatsapp_form_number` e `release_date`
  **só se a chave vier** no payload (`"x" in fields`), como já faz com `google_review_url`.
- Tag: `^[a-z0-9][a-z0-9_.-]{1,62}$` após `lstrip("$")` e `lower()`; troca grava audit
  `"InfiniteTag: 'antiga' → 'nova'"`.
- Segredo novo: o GET de configurações passa a devolver `virtuais_pedidos_aguardando` (contagem); o
  front pede confirmação com esse número; `setRegenerarToken(false)` no `onSuccess`. Para não matar
  links abertos, o token anterior é guardado em `infinitepay_webhook_token_anterior` e aceito por 24 h
  (`..._anterior_ate`).

## R8 — IP do cliente (FR-027)

**Decisão**: o `frontend/server.js` (que já é o único caminho público de `/api`) põe um cabeçalho
`X-Manto-Client-Ip` com o **último** item do `X-Forwarded-For` que ele recebeu da borda do Render (o
IP que a borda viu conectar) — ou `req.socket.remoteAddress` sem cabeçalho. No Flask, `ip_do_cliente()`
(em `app/api_utils.py`) usa esse cabeçalho; sem ele, `request.remote_addr`. O `Limiter` e o
`origin_ip` da reserva passam a usá-lo.

**Por quê**: contar saltos (`ProxyFix x_for=N`) dá resultado diferente para quem chama o backend
direto (`manto-backend.onrender.com`, 1 salto) e para quem vem pelo Node (≥ 3). Forjar o cabeçalho
chamando o backend direto só muda o balde do próprio atacante — o mesmo que ele já consegue trocando de
IP. **A conferir em produção depois do deploy** (quickstart, passo 3): um log de uma linha por reserva
com a contagem de itens do XFF e se o IP resolvido é público (sem o IP em si).

**Efeito colateral desejado**: o limite de login (10/min) e os outros `@limiter.limit` deixam de valer
para a empresa inteira.

## R9 — Antecedência de reserva (FR-006)

`VIRTUAL_ANTECEDENCIA_RESERVA_HORAS = 2` (decisão do dono). `listar_slots_disponiveis` e
`_travar_slot` usam `start_at > agora() + 2 h`. Constante, não coluna.

## R10 — Pagamentos a conferir (FR-012, FR-031–FR-033)

Lista única, lida por `GET /api/virtuais/pagamentos-a-conferir`, com três origens:

1. avisos com desfecho `divergente`, `orfao`, `retido` esgotado, ou `devolucao_aberta` ainda sem
   devolução concluída não entram (já estão em Devoluções);
2. pedidos liberados com `expired_unverified` **por `nao_sei`** (operadora fora) — não por abandono;
3. falha de link (`payment_link_error`) agrupada por código na última hora (para o
   `external_checkout_not_enabled` aparecer uma vez, não 50).

Cada item tem `resolvido_em/por` (PATCH com auditoria). Sino: `KIND_VIRTUAL_ATENCAO =
"virtual.atencao"` para COMERCIAL e SUPERADMIN, dedupe por item. Recibo (`receipt_url`) guardado no
pedido quando chega por aviso ou retorno.

## R11 — Sala do Meet até a chamada (FR-038, FR-039)

`retentar_salas` passa a: 3 tentativas nos minutos 0/1/2 (como hoje) e depois uma a cada 10 min até
`start_at`; faltando < 6 h com `meet_pending`, notificação `virtual.atencao` (uma por pedido).
Eventos criados pela loja levam `extendedProperties.private.manto_virtual_nsu`; a sincronização da
agenda pula itens com essa marca (mesmo lugar onde já pula `_is_manto_task_item`). `insert_event`
ganha o parâmetro opcional `private_props`.

## R12 — API nova da InfinitePay (FR-040)

`INFINITEPAY_API_KEY` em `app/config.py`, default `""` (variável no Render com `sync: false`; nunca lida
pela API, nunca no SiteSetting — o SiteSetting vai para o backup e para o espelho). Com chave: header
`X-Api-Key` nas duas chamadas e `options = {valid_until: <fim da trava com fuso -03:00>,
single_payment: true}` no `/links`. `webhook_url` continua string (o formato por eventos não tem exemplo
publicado). Sem chave: exatamente o fluxo provado no teste A.

## R13 — Telefone e descrição enviados à operadora (FR-028)

**Decisão**: telefone **continua só com dígitos** — foi o formato aceito em produção no teste A (a doc
mostra `+55…`; trocar seria arriscar o que já funciona). Descrição: `"<título da campanha> — pedido
<order_nsu>"`. `customer = {email, phone_number}` sem `name`.

## R14 — Campanha fora da vitrine e limpeza de teste (FR-041, FR-042)

Coluna `virtual_campaigns.listada` (bool, default true); `listar_vitrine` filtra; a gestão ganha a
chave. Limpeza de venda de teste: `specs/310-…/limpar_venda_teste.py --pedido N [--execute]`, no molde
do que foi feito à mão em 20/10 (pausa, Google delete respeitando a trava, horário livre, pedido
cancelado, escala e evento apagados, auditoria).

## R15 — Cancelar pedido pago (FR-034)

`POST /api/virtuais/pedidos/<id>/cancelar` (COMERCIAL, SUPERADMIN), confirmação no front. Em
`cancelar_pedido_pago(order, motivo_texto)`: trava pedido → horário; pedido `cancelado`; horário
`livre` (se `start_at > agora() + 2 h`; senão fica `vendido` sem dono para não reaparecer em cima da
hora — a contagem de "tomado" trata); evento local e Google apagados (trava respeitada); entrega e
presente 3D pendentes removidos (`ops3d` remove o gift do evento); devolução `desistencia` com o valor
pago; e-mail de cancelamento. A venda sai dos relatórios porque o `CalendarEvent` deixa de existir.

## R16 — Família (FR-035–FR-037)

- Reserva e pedido passam a devolver `seconds_left` (calculado no servidor); o front conta a partir
  dele.
- `client_token` só reaproveita o pedido se `slot_id`, `modality`, `gift_item_id` e `child_name`
  forem iguais; o front renova o token depois de cada 201.
- Estados da página: `reservado` sem link → "Gerando o pagamento…"; `aguardando` → "Ainda não
  identificamos o pagamento" com botão "Ir para o pagamento"; com aviso/retorno em processamento →
  "Confirmando o pagamento…". `refetchInterval` também em `reservado`.

## Pontos que só a operadora real fecha (fica no quickstart, testes B e C)

- Se a reconsulta **com** identificadores de um Pix pago e devolvido responde `paid:true` ou outra
  coisa (afeta a limpeza de teste).
- Se o link legado aceita segundo pagamento (pagamento em dobro).
- Formato e política de reenvio do aviso fora do 200.
