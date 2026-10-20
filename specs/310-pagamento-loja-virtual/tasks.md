---
description: "Tasks da 310 — pagamento da loja de conversas ligado com segurança"
---
# Tasks: 310 — Pagamento da loja de conversas ligado com segurança (InfinitePay)

**Input**: `specs/310-pagamento-loja-virtual/` (spec com R-01–R-22, plan, research R1–R16,
data-model, contracts/api-310.md, quickstart)

**Verificação (Princípio VIII)**: `verify_310.py` nasce na Fase 2, ANTES do núcleo, e roda contra
`98192e8` com os cenários marcados "deve falhar no HEAD" falhando pelo motivo certo. InfinitePay e
Google são dublês que falham fechado (nenhuma rede); concorrência com duas conexões reais e
`threading.Barrier`; prova por mutação roda a sonda limpa antes da mutada; escrita conferida por
conexão separada; limpeza no `finally`.

**Ambiente**: worktree `C:\tmp\mp310`; Python do repo principal
(`C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe`); `.local-db-url` copiado; nunca
`git checkout` no diretório principal (outros chats). Commits `feat(310)`/`docs(310)` por caminho.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [x] T001 Rebase do worktree na `origin/main` do dia (a 306 já entrou na main) e conferir a cabeça
      das migrations; anotar em `data-model.md` o `down_revision` real
- [x] T002 [P] Constantes em `app/constants.py`: `VIRTUAL_ANTECEDENCIA_RESERVA_HORAS=2`,
      `VIRTUAL_MIN_MINUTOS_NO_PAGAMENTO=30`, `VIRTUAL_SALA_ALERTA_HORAS=6`,
      `VIRTUAL_SALA_RETRY_LONGO_MIN=10`, `VIRTUAL_AVISO_REPROCESSA_HORAS=48`, motivos de devolução
      novos (+ rótulos em `VIRTUAL_REFUND_REASON_LABELS`), desfechos do aviso (finais/não finais, R-06)

---

## Phase 2: Foundational (bloqueia todas as histórias)

- [x] T003 Colunas novas em `app/models.py` conforme `data-model.md` (SiteSetting, VirtualOrder,
      VirtualPaymentNotification, VirtualCampaign), com docstring do porquê
- [x] T004 Migration manual `migrations/versions/<rev>_pagamento_loja_virtual_310.py` (aditiva +
      backfill `state='decidido'` onde `outcome` não é nulo; downgrade completo); aplicar no
      `manto_local`; ida e volta
- [x] T005 [P] Trava `_suppress_infinitepay()` + config `INFINITEPAY_SUPPRESS_CALLS` e
      `INFINITEPAY_API_KEY` (default `""`) em `app/config.py` (R5, R12; molde da 303); o
      `create_app` registra uma linha no log da subida quando a chave está ausente ("link sem
      validade — fluxo legado", constituição XIV)
- [x] T006 Cliente `app/integracoes/infinitepay_client.py`: resultado de reconsulta em 4 valores
      (`pago`/`nao_pago`/`nao_encontrado`/`nao_sei`, R4) com `success:false` = `nao_encontrado`;
      `InfinitePayRecusou` carrega `code` (`body.error` ou `message`) e status; `InfinitePayTravada`
      (subclasse de Indisponível) quando a config injetada manda travar; header `X-Api-Key` e
      `options{valid_until, single_payment}` só com chave; descrição/`customer` como R-15 (sem
      `import flask` no topo — config por parâmetro)
- [x] T007 **`specs/310-pagamento-loja-virtual/verify_310.py`** — os 44 cenários da seção
      "Verificação" da spec + R-22 (20 rodadas de concorrência); dublês de InfinitePay (por resultado e
      por identificadores) e de Google (conta chamadas, falha fechado); cenários por bloco (`--ate`),
      registro de qual caminho decidiu; escrito AGORA
- [x] T008 Rodar `verify_310.py` contra o núcleo de `98192e8` (só fundação aplicada): cenários
      1–6, 13, 15, 18, 26, 29 FALHAM pelo motivo descrito; registrar a saída em
      `specs/310-pagamento-loja-virtual/verify_baseline.txt`

**Checkpoint**: verify falhando pelos motivos certos → núcleo pode começar.

---

## Phase 3: US1 — Um horário, uma família (P1) 🎯 MVP

**Objetivo**: nenhuma combinação de atraso/concorrência vende o mesmo horário duas vezes.
**Teste independente**: cenários 1–7 e R-22 do verify.

- [ ] T009 [US1] `decidir_pagamento(order_id, consulta, *, identificadores, origem)` em
      `app/marketing/virtuais_ops.py` com a ordem de R-01 e travas pedido → horário → campanha
      (`with_for_update` + `populate_existing`); `_pagamento_confere` (R-02); retorna o desfecho
- [ ] T010 [US1] `efetivar_pedido` reescrito para gravar tudo no banco primeiro (pedido pago, horário
      vendido com `order_id`, evento com id local e `meet_pending`, entrega, presente) e só depois,
      fora das travas, criar o evento Google pelo caminho de `regerar_sala` e enviar o e-mail
- [ ] T011 [US1] `_liberar_reserva` trava o pedido antes do horário, relê o status (só libera ATIVOS)
      e nunca solta horário `vendido`
- [ ] T012 [US1] `expirar_reservas` usa `decidir_pagamento`; `try/rollback` por pedido; contador de
      reconsulta separado; `nao_encontrado` sem identificadores = libera numa consulta; `nao_sei`
      retém o horário de fato (estende `slot.locked_until`) e, esgotado, marca
      `unverified_reason='nao_sei'`; usa identificadores de avisos com token certo do mesmo
      `order_nsu` (R-09)
- [ ] T013 [US1] Vaga de vídeo: reservas ativas de vídeo ocupam vaga durante a trava em
      `reservar`/`recorded_available`; conferência na efetivação (R-03)
- [ ] T014 [US1] Antecedência de 2 h em `listar_slots_disponiveis` e `_travar_slot` (409 com a frase
      do contrato) e folga de 30 min em `decidir_pagamento`
- [ ] T015 [US1] Rodar cenários 1–7 + R-22 (20×) até verde; prova por mutação: desligar a checagem de
      dono e a trava do pedido e ver os cenários 1–3 acusarem

---

## Phase 4: US2 — Todo pagamento termina em venda ou devolução (P1)

**Objetivo**: pagamento provado nunca fica sem dono. **Teste**: cenários 8–15.

- [ ] T016 [US2] Rota do aviso `app/api/virtuais_webhook.py`: corpo > 64 KB → 413; token atual ou
      anterior (24 h) por `hmac.compare_digest`; grava `pendente` e responde 200; dispara thread com
      `app_context` para `processar_aviso(id)`; token inválido → 404 com `transaction_nsu=NULL` e
      resumo de 2 KB; `@limiter.limit("60 per minute")`
- [ ] T017 [US2] `processar_aviso(id)` em `virtuais_ops.py`: claim por linha (`pendente→processando`),
      reconsulta com os identificadores DO AVISO, `decidir_pagamento`, grava identificadores e recibo
      só depois da prova (FR-017); reentrega de aviso não final é reprocessada
- [ ] T018 [US2] Reprocessamento na varredura (`ciclo_de_varredura` ganha a rotina "avisos"):
      política 0/1/2 min e depois 10 em 10 até 48 h; esgotou → "a conferir" (R-06)
- [ ] T019 [US2] Pagamento em dobro (`pagamento_em_dobro`, pedido segue pago) e pagamento de pedido
      cancelado (`pagamento_sem_pedido_ativo`) em `decidir_pagamento` + devolução com o valor da
      reconsulta da cobrança nova
- [ ] T020 [US2] Endpoint `POST /api/virtuais/pedidos/<token>/retorno` em `app/api/virtuais_public.py`
      (contrato; R-08; limite 20/min por IP do cliente) chamando `registrar_retorno` em `virtuais_ops.py`
- [ ] T021 [P] [US2] `PedidoVirtualPage.tsx` lê a query do retorno uma vez, chama o endpoint e limpa a
      URL (`history.replaceState`); hook em `frontend/apps/public/src/lib/virtuais.ts`
- [ ] T022 [US2] Rodar cenários 8–15 até verde (o 8 mede o tempo do retorno até "pago", SC-003); mutação: gravar identificadores antes da prova →
      cenário 15 acusa

---

## Phase 5: US3 — Ligar e desligar com segurança (P1)

**Teste**: cenários 16–24.

- [ ] T023 [US3] `_gerar_link_pagamento`: confere interruptor e config (R-18, 503 "reservas
      fechadas"); `InfinitePayRecusou` não é repetido; grava `payment_link_error`; mensagem do
      contrato; travado → "Pagamento travado neste ambiente (cópia de teste)"; pedido com falha de
      link fora do teto por origem
- [ ] T024 [US3] `_criar_evento_google` e o apagamento de evento da loja respeitam
      `CALENDAR_SUPPRESS_EVENT_WRITES` (docstring em `app/config.py` atualizado)
- [ ] T025 [US3] `_campos_faltantes_para_publicar` recusa sem handle, sem token ou interruptor
      desligado (campo `pagamento`)
- [ ] T026 [US3] `app/admin/config_ops.py`: e-mail/WhatsApp/data de corte só se a chave vier; tag
      validada (regex de R7) e audit antigo→novo; regerar guarda o anterior por 24 h; interruptor
- [ ] T027 [P] [US3] `app/api/admin_config_read.py`: `virtuais_pagamento_ativo` e
      `virtuais_pedidos_aguardando`
- [ ] T028 [P] [US3] `AdminSettingsPage.tsx` + `lib/adminConfig.ts`: interruptor; confirmação com a
      contagem antes de regerar; caixa volta a desmarcada no `onSuccess`; erro de tag no campo
- [ ] T029 [US3] Sino `KIND_VIRTUAL_ATENCAO` em `app/notificacoes/notificacoes_ops.py` (COMERCIAL,
      SUPERADMIN) e disparo na falha de link (dedupe por código/hora, R-19)
- [ ] T030 [US3] Rodar cenários 16–24 até verde

---

## Phase 6: US4 — Limites por família (P1)

**Teste**: cenários 25–26.

- [ ] T031 [US4] `frontend/server.js`: `X-Manto-Client-Ip` = último item do XFF recebido (ou
      `req.socket.remoteAddress`) nas requisições repassadas a `/api`
- [ ] T032 [US4] `ip_do_cliente()` em `app/api_utils.py`; `key_func` do `Limiter` em `app/__init__.py`
      e `origin_ip` da reserva em `virtuais_public.py` passam a usá-lo; log de uma linha
      `[virtuais] origem: xff_itens=N publico=sim|nao` (sem o IP)
- [ ] T033 [US4] Rodar cenários 25–26; `node --check frontend/server.js`

---

## Phase 7: US5 — Privacidade e segredo (P1)

**Teste**: cenários 27–29.

- [ ] T034 [US5] Pacote à operadora como R-15 (já no cliente, T006) conferido no dublê pelo cenário 27
- [ ] T035 [P] [US5] Filtro de log no `gunicorn.access` (registrado no `create_app`) mascarando
      `/webhooks/infinitepay/<…>`; mesma máscara nos `console.error` do proxy em `frontend/server.js`;
      `logger` da loja nunca imprime o token
- [ ] T036 [US5] Rodar cenários 27–29

---

## Phase 8: US6 — A equipe vê o que precisa de ação (P2)

**Teste**: cenários 30–32 e 36.

- [ ] T037 [US6] `listar_a_conferir()` e `resolver_a_conferir()` em `virtuais_ops.py` (R-07; audit)
- [ ] T038 [US6] `GET /api/virtuais/pagamentos-a-conferir` em `virtuais_read.py` e `PATCH …/<tipo>/<id>`
      em `virtuais_write.py` (COMERCIAL, SUPERADMIN; função de RBAC no início da view)
- [ ] T039 [US6] `cancelar_pedido_pago(order, motivo)` em `virtuais_ops.py` (R15, R-19: travas,
      horário, evento local e Google, entrega, presente via `delete_event_gift` se a impressão não
      começou — se começou, fica e entra em "a conferir" (R-04) —, devolução
      `desistencia`, e-mail) + `POST /api/virtuais/pedidos/<id>/cancelar` em `virtuais_write.py`
- [ ] T040 [P] [US6] `VirtuaisDevolucoesPage.tsx`: aba "Pagamentos a conferir" (NSU, slug, recibo,
      data, valor) com "marcar como resolvido"; mostrar `order_nsu` e data nas devoluções
- [ ] T041 [P] [US6] Botão "Cancelar e abrir devolução" com confirmação e motivo na linha do pedido
      pago da Fila de Produção (`frontend/apps/internal/src/pages/FilaProducaoMidiaPage.tsx`, rota
      `/virtuais/producao`) + hook em `frontend/apps/internal/src/lib/virtuais.ts`
- [ ] T042 [US6] Sino na devolução nova e no "a conferir" novo (dedupe por item)
- [ ] T043 [US6] Rodar cenários 30–32 e 36

---

## Phase 9: US7 — A família entende onde está (P2)

**Teste**: cenários 33–35 + tela aberta 375×812.

- [ ] T044 [US7] `seconds_left` e `confirming` em `serialize` do pedido e na resposta de reserva
- [ ] T045 [US7] `client_token` só reaproveita com horário, formato, presente e criança iguais
      (`reservar`)
- [ ] T046 [P] [US7] `CampanhaVirtualPage.tsx` / `PedidoVirtualPage.tsx` / `lib/virtuais.ts`:
      contagem por `seconds_left`; token novo depois de cada 201; três estados de espera com
      textos distintos; `refetchInterval` também em `reservado`
- [ ] T047 [US7] Rodar cenários 33–35

---

## Phase 10: US8 — Sala do Meet até a chamada (P2)

**Teste**: cenários 37–38.

- [ ] T048 [US8] `retentar_salas`: depois das 3 tentativas, a cada 10 min até `start_at`; alerta no
      sino com menos de 6 h (um por pedido)
- [ ] T049 [US8] `insert_event(..., private_props=None)` em `app/calendar/service.py`; a loja marca
      `manto_virtual_nsu`; a sincronização em `app/calendar/routes.py` pula itens com a marca (ao lado
      de `_is_manto_task_item`)
- [ ] T050 [US8] Rodar cenários 37–38

---

## Phase 11: US9 — Link vence junto com a reserva (P2)

**Teste**: cenários 39–40.

- [ ] T051 [US9] Com `INFINITEPAY_API_KEY`: `valid_until` = fim da trava em ISO com `-03:00` e
      `single_payment=true` (T006 já monta; aqui o `_gerar_link_pagamento` passa o fim da trava)
- [ ] T052 [US9] Rodar cenários 39–40; `render.yaml` ganha `INFINITEPAY_API_KEY` com `sync: false`

---

## Phase 12: US10 — Teste real e operação (P1)

**Teste**: cenários 41–42 + quickstart §2 com o dono.

- [ ] T053 [US10] `listada` em `listar_vitrine`, no PATCH da campanha e na tela de gestão
- [ ] T054 [P] [US10] `specs/310-pagamento-loja-virtual/limpar_venda_teste.py --pedido N [--execute]`
      (R-21; trava do Google respeitada; auditoria)
- [ ] T055 [US10] Rodar cenários 41–42

---

## Phase 13: Polish & cross-cutting

- [ ] T056 Regressão: `verify_205.py` e `verify_304.py` verdes; `verify_310.py` 44/44 + R-22
- [ ] T057 `cd frontend && npm run typecheck`; `ruff check` nos tocados; `ruff format` só nos novos
- [ ] T058 Tela aberta (Flask do worktree em 127.0.0.1:5001, Vite em 127.0.0.1:5183): roteiro do
      quickstart §1
- [ ] T059 Revisão adversarial por workflow (finders por dimensão + um cético por achado) do diff
      inteiro antes do commit final
- [ ] T060 Docs: `docs/01` (§4.3 RBAC, contratos, variáveis), `docs/02` (telas), `docs/03` (entrada
      no topo + índice), `docs/04` (máquina de estados e invariantes), `docs/05` (registra o limitador em
      memória por processo e "História 9 desligada até a API Key"; não mexe no item 88), `DEVELOPMENT.md` (§Operar a produção:
      ligar/desligar a loja, teste de R$ 1, trava local, regra R-20), skill `manto-deploy` (R-20)
- [ ] T061 `/speckit-converge` até não sobrar tarefa nova
- [ ] T062 Pré-merge: rebase na `main` do dia; reencadear `down_revision`; ensaio de
      upgrade/downgrade num banco descartável com o dump do dia; venv 3.11 com `requirements.txt`;
      relatório ao dono. **Sem push** até ele pedir.

---

## Dependências

- Fase 1 → Fase 2 → US1 → US2 (o aviso e o retorno usam `decidir_pagamento`).
- US3, US4, US5 dependem só da Fase 2 (podem andar em paralelo a US1/US2 em arquivos distintos, mas
  US3 mexe em `virtuais_ops.py` — serializar com US1/US2 nesse arquivo).
- US6 depende de US2 (desfechos e devoluções); US7 de US1; US8 de US1 (efetivar no banco primeiro);
  US9 de T006; US10 de US3 (publicar) e US6 (limpeza usa o cancelamento).
- Polish depois de tudo; testes A e C com o dono só depois do deploy.

## Paralelo (exemplos)

- T005 ∥ T002; T021 ∥ T020 (front × back); T027 ∥ T028; T035 ∥ T034; T040 ∥ T041; T046 ∥ T044;
  T054 ∥ T053.

## Estratégia

MVP = Fases 1–2 + US1 + US2 + US3 (sem elas não se liga a loja). US4 e US5 entram no mesmo deploy
(baratas e de risco). US6–US10 completam a operação para o Natal. Um deploy só, à noite, com o
interruptor desligado; o dono liga depois dos testes A e C.
