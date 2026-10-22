---
description: "Tasks da feature 315 — pedido de cancelamento pelo sistema"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Feature 315 — o Comercial pede o cancelamento e o Superadmin decide

**Input**: artefatos em `/specs/315-pedido-de-cancelamento/`

**Pré-requisitos**: plan.md, spec.md (histórias e "Verificação"), research.md (R1–R12), data-model.md,
contracts/api.md, `pesquisa/reconferencia-2026-10-22.md` (as linhas `arquivo:linha` abaixo vêm dela, contra
`7cc5e11e`).

**Verificação (Princípio VIII)**: `verify_315.py` inteiro na Foundational, antes do núcleo; a primeira rodada contra o
código de hoje (só com a migration aplicada) fica em `verify_315_primeira_falha.txt`.

**Histórias** (spec): US1 = pedir (H1), US2 = ver enquanto espera (H2), US3 = decidir (H3). Ordem: US1 → US2 → US3 (o
corte e a herança da US2 leem o pedido que a US1 grava; o fecho da US3 lê as cinco colunas).

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 Conferir `.specify/feature.json` → `specs/315-pedido-de-cancelamento`; `env315.ps1` no scratchpad (já
      criado, `C:\tmp\mp315`); `.local-db-url` e `frontend/node_modules` no worktree (já feitos)
- [X] T002 Migration à mão `migrations/versions/<rev>_solicitacao_de_cancelamento.py` (`down_revision =
      "c5d2f7a9e306"`; `add_column` de `deletion_request_scope String(16)` e `deletion_request_refund Text`, nulas;
      `downgrade` = `drop_column` das duas) e as duas colunas em `app/models.py` ao lado de `:304-306`, com comentário do
      porquê; `flask db heads` com um head só no worktree; no `manto_local` (que está na 310, `e8b4a1c7d310`) as duas
      colunas entram por `ADD COLUMN IF NOT EXISTS`, sem mexer no `alembic_version`
- [X] T003 Base da regressão no HEAD (com a migration aplicada): `specs/306-…/verify_306.py` (base 67/69),
      `specs/312-…/verify_312.py` (27/27), `specs/303-…/verify_303.py`, `specs/311-…/verify_311.py`,
      `specs/302-…/verify_302.py` — anotar os números (**base 22/10**: 306 67/69, 312 27/27, 303 44/44, 311 8/8, 302 22/22; o `scripts/db/verify_cancelamento_evento.py` fica fora: dívidas
      85 e 129)

---

## Phase 2: Foundational (bloqueia as histórias)

- [X] T004 Escrever `specs/315-pedido-de-cancelamento/verify_315.py` inteiro, cenários 1–28 da spec, importando o harness
      da 306 como a 312 faz (`verify_312.py:7-13`, `:46-49`: `GoogleFalso`, disjuntor, e-mail falso, `_usuario`,
      `_externo`, `_sob_mutacao` `verify_306.py:6895`); prefixo `__v315_`; eventos descartáveis em 2050; vendas de
      vários dias criadas pelos endpoints de agrupar; cachê pago marcado pelo endpoint de status; o pedido "de antes do
      deploy" (cenário 25) semeado por SQL nas três colunas (o molde `verify_312.py:225-229` semeia só `at` e `by_id`;
      aqui também o `reason`); o cenário 26 exige o 403 também na rota nova (404 hoje — senão passaria contra o código de
      hoje); o 6 confere o 409 na porta e o `pedido_bloqueado` no detalhe; sai 2 se houver backend local
      rodando; `--so=` para iterar
- [X] T005 Rodar o `verify_315.py` contra o código de hoje e guardar a saída em
      `specs/315-pedido-de-cancelamento/verify_315_primeira_falha.txt`. Esperado: verdes só 27 (regressão) e 28
      (limpeza) — os cenários pedem pela rota nova, que ainda dá 404; o resto vermelho pelo motivo certo (rota nova 404,
      aviso ausente, corte ausente, `pedidos` ausente…)

---

## Phase 3: US1 — Pedir (P1) 🎯

**Meta**: o Comercial pede com motivo, alcance e devolução; o pedido grava e avisa os Superadmins.
**Teste independente**: cenários 1–5, 7–9, 16, 17, 26 (o 6 inteiro precisa do detalhe da US2).

- [X] T006 [US1] `app/constants.py` (ao lado de `:616-649`): `CODIGO_PEDIDO_PENDENTE = "pedido_pendente"`,
      `CODIGO_SEM_PEDIDO = "sem_pedido"` e a união `CODIGOS_RECUSA_DO_PEDIDO` (com `cancelado`, `ensaio`,
      `cache_pago`). Os kinds do sino **não** moram aqui: ficam no catálogo de `notificacoes_ops.py:54-60` (T007)
- [X] T007 [US1] `app/notificacoes/notificacoes_ops.py`: os dois kinds no catálogo e em `DESTINATARIOS_POR_KIND`
      (`:54-77`; receita na docstring `:15-17`); `notificar_pedido_cancelamento(event, *, carimbo, n_escalados,
      autor_nome)` no molde de `notificar_evento_sumiu_google` (`:355-386`) — urgente em ≤ 7 dias ou passado (`:272`,
      `:311`), corpo com data · venda · recebido · N escalados · alcance · quem pediu · motivo, cortado em 500;
      `notificar_pedido_decidido(event_id, *, autor, quem_decidiu_id, titulo, corpo, link)` com
      `destinatarios=[autor]` (`:153-160` não filtra: o produtor filtra `autor.is_active and autor.has_access and
      autor.id != quem_decidiu_id`), sem entidade e sem link no "excluído"
- [X] T008 [US1] `app/calendar/solicitacao_ops.py` (NOVO, research R1): `ler_corpo` (forma R4: `motivo`, `alcance`,
      `devolucao_*`, `venda_nova` — esta proibida fora do pedido de um dia só —, todos os erros de uma vez; venda
      virtual só motivo; Nada sem nome/PIX; pelo caminho velho sem `devolucao` e sem `alcance` → colunas nulas),
      `alcance_do_evento` (R3), `bloqueio_do_proprio_dia(event)` (ensaio pelo tipo; cachê pago **do próprio dia** pela
      régua `cancel_ops._papeis_com_cache_pago(ids)` `:2203-2218`, frase `FRASE_CACHE_PAGO` `:2224`),
      `n_escalados(ids)` pela régua do cancelamento (`len(cancel_ops.elenco_dos_dias(ids))`, ~`:2180-2197`: sem
      convite recusado e sem a vaga de presença; nos dias que o pedido alcança) e `solicitar(event, corpo, actor, *,
      caminho_velho)` na ordem do contrato: `exigir_evento_vivo` (`cancel_ops.py:3113-3117`) → 409 ensaio → 409
      cache_pago do próprio dia → 400 campos → 409 cache_pago dos outros dias que "todos" alcança → claim `UPDATE …
      WHERE deletion_requested_at IS NULL AND cancelled_at IS NULL` com `synchronize_session=False` (molde
      `sumico_ops.py:225-238`) e `db.session.refresh(event)` nos **dois** ramos (perdeu → 409 cancelado ou
      pedido_pendente com o nome); nada no request atribui as colunas no objeto fora do UPDATE (autoflush); `EventLog`
      sem `created_at`; `_log_sync("cancel_requested", …)` (`routes.py:376`); o aviso; commit. `serializar_devolucao`
      tolerante a JSON corrompido
- [X] T009 [US1] `app/api/agenda_write.py`: nas views de hoje (`:908-930`, `:932-948`) as regras novas
      `/events/<id>/pedido-cancelamento` (POST/DELETE) além das velhas (R9 — os nomes de endpoint não mudam, o 9b do
      `verify_312` segue certo); o POST chama `solicitacao_ops.solicitar` com `caminho_velho` pela `request.url_rule`;
      erros por `json_error(..., codigo=…)`; 200 com `serialize_event_detail` (molde do devolver-ao-google); o DELETE
      continua no `recusar_solicitacao` de hoje até a T018 (só ganha a rota nova e o gate `_can_delete`, papel real);
      docstrings com o RBAC
- [X] T010 [US1] `app/calendar/cancel_ops.py`: tirar **só** `solicitar_exclusao` (`:3502-3521`, que gravava o
      `EventLog` em SP — dívida 76); o único chamador é `agenda_write.py:922`. O `recusar_solicitacao` (`:3524-3541`) sai
      na T018
- [X] T011 [US1] Rodar `verify_315.py '--so=1,2,3,4,5,7,8,9,16,17,26'` — verdes; os outros seguem vermelhos; commit
      `feat(315): pedir — a forma da 306, as recusas, o claim e o aviso aos Superadmins`

**Checkpoint**: verdes 1–5, 7–9, 16, 17, 26, 27, 28.

---

## Phase 4: US2 — Ver enquanto espera (P1)

**Meta**: quadro com o corte, faixa, selo, herança do satélite e portal.
**Teste independente**: cenários 6, 10–12, 14, 15 (o 13 e o 25 fecham na US3: pedem a decisão).

- [X] T012 [US2] `app/calendar/solicitacao_ops.py`: `serializar_para(event, *, flags, usuario, impersonando)` — o bloco
      do pedido com o corte do `data-model.md`: motivo/autor e modo/valor por `show_comercial`; nome/PIX por
      `show_comercial` **e** (`show_financeiro` **ou** o autor sem "Ver como"); `flags is None` (chamador interno) libera
      tudo, como hoje; `solicitacoes_da_venda(eventos) -> dict[int, datetime]` (uma consulta pelos `group_leader_id`
      distintos, alcance `todos` ou nulo, R6); `faixa_das_solicitacoes()` (função própria: `sumico_ops.faixa_sumidos`
      `:542-580` fica intacta — o `verify_303.py:1955` a chama direto e confere `total` e `items` só do sumiço);
      `escolha_do_alcance(event)` — no principal com outro dia vivo, `{dias: N, proximo: {id, start_at}}` pelo mesmo
      critério da passagem da 306 (`cancel_ops.py:1220-1225`, pula compromisso interno), para a tela não escolher o dia
- [X] T013 [US2] `app/api/agenda_read.py` `serialize_event_detail(event, user, impersonate)` (`:814`, `flags`
      `:822`): o bloco `deletion_request` (`:854-862`) pelo `serializar_para` com `user` (não `current_user`);
      `pedido_bloqueado` (o bloqueio do próprio dia; só se `can_request_delete` e não pendente) e `escolha_do_alcance`;
      `pedido_da_venda` e `situacao = exclusao_solicitada` no satélite que herda (lê o principal direto, um evento) —
      tudo **antes** do retorno antecipado do ENSAIO (`:903-905`); `serialize_event_summary(event,
      pedido_da_venda=None)` (`:70-95`) com a `situacao` herdada; o **mês** (`build_agenda_month`, `:128-138`, chamado
      de `agenda.py:48`) com o lote
- [X] T014 [US2] `app/api/agenda.py`: a **busca** (`api_agenda_search`, `:51-77`, a lista em `:71`) e o **dia** (`:104`)
      chamam o lote uma vez; a faixa (`:160-172`) ganha `pedidos` por `faixa_das_solicitacoes()`, pelo mesmo gate
      `_ve_faixa_sumidos` (`:154-157`), com `total`/`items` intactos
- [X] T015 [US2] `app/calendar/cancel_ops.py` `listar_cancelamentos(*, flags, mes, devolucao)` (`:3564`): ganha
      `usuario` (e a view `agenda_write.py:985-986` passa `current_user`); os `pendentes[]` (`:3611-3625`) pelo
      `serializar_para` com `ver_motivo` (`:3605`) — alcance e devolução, e o corte também no "Ver como"
- [X] T016 [US2] `app/talent_portal/portal_ops.py`: `em_confirmacao` (`:321`) = marca ou pedido ou pedido da venda;
      `_role_summary` (`:268-332`) recebe o lote; `get_agenda` (o `resumo` de `:398`, sobre convites, próximos e
      passados) e `get_historico` (`:936`) chamam o lote uma vez; o comentário de `:318-320` atualizado (sem motivo;
      uma consulta por lista)
- [X] T017 [US2] Rodar `verify_315.py '--so=6,10,11,12,14,15'` e os de US1 — verdes; commit `feat(315): ver enquanto
      espera — o corte da Q6, a faixa, o selo, o satélite e o portal`

**Checkpoint**: verdes 1–12, 14–17, 26, 27, 28.

---

## Phase 5: US3 — Decidir (P1)

**Meta**: recusar, cancelar e excluir fecham o pedido e respondem a quem pediu, uma vez.
**Teste independente**: cenários 13, 18–25.

- [X] T018 [US3] `app/calendar/solicitacao_ops.py`: `recusar(event, *, actor, motivo)` — claim `UPDATE … SET <cinco
      colunas>=NULL WHERE deletion_requested_at = :carimbo_lido` com `refresh(event)` (perdeu → 409 `sem_pedido`),
      `EventLog` sem `created_at`, `_log_sync("cancel_request_refused", …)`,
      `marcar_lidas_por_entidade("calendar_event", id, kind="evento.pedido_cancelamento")` (`notificacoes_ops.py:458-474`
      — sempre com o kind, senão marca o `pedido_decidido`), resposta "Pedido recusado — <título>: <motivo>" (sem motivo:
      "Pedido recusado — <título>"), commit; a view `DELETE` (`agenda_write.py:932-948`) passa a chamá-lo e o
      `recusar_solicitacao` de `cancel_ops.py:3524-3541` sai (único chamador `agenda_write.py:942`)
- [X] T019 [US3] `app/calendar/solicitacao_ops.py` `fechar_no_cancelamento(dia, *, alcance, novo_principal)` e
      `app/calendar/cancel_ops.py`: `ao_cancelar` (`:1594-1602`) passa a chamá-lo (import tardio; assinatura intacta — o
      espião do `verify_306.py:384-412` envolve e chama o real); as três linhas que zeravam o pedido em
      `_encerrar_os_dias` (`:2059-2061`) saem (o fecho zera as cinco, lendo autor/alcance/carimbo antes); avisos do
      pedido lidos (com o kind); quem cancelou = `dia.cancelled_by_id` (`:2056`); as respostas, literais: avulso ou
      "todos" → "Evento cancelado — <título> (dd/mm)"; corte de um dia → "Dia dd/mm cancelado — <título>: a venda segue
      nos outros dias"; passagem (o 1º dia sozinho) → "Dia dd/mm cancelado — <título>: a venda passou para o dia dd/mm;
      os outros dias seguem". O pedido legado num ensaio, que o ato apaga do banco (`:2068`), sai sem resposta (aceito:
      ensaio não recebe pedido novo)
- [X] T020 [US3] `solicitacao_ops.responder_na_exclusao(autor_id, titulo, carimbo, *, quem_excluiu)` e
      `app/api/agenda_write.py` `api_delete_event` (`:669-718`): antes de `_delete_event_flow`, guardar autor, título e
      carimbo do pedido (o objeto morre no commit, `routes.py:4586`); depois de `deleted`, chamar
      `responder_na_exclusao` em transação própria — "Evento excluído — <título>", sem entidade e sem link; não responde
      se quem exclui é o autor; falha no aviso não desfaz a exclusão (`apagar_por_entidade` `routes.py:354` já apaga os
      avisos do pedido). Corrida aceita: uma recusa que commita entre a leitura e a trava do núcleo
      (`routes.py:~4563`) dá ao autor "recusado" e depois "excluído" — registrada no research R10
- [ ] T021 [US3] Rodar `verify_315.py '--so=13,18,19,20,21,22,23,24,25'` e os anteriores — verdes; `verify_306` e
      `verify_312` sem regressão; commit `feat(315): decidir — recusar, o fecho no cancelamento e a resposta na exclusão`

**Checkpoint**: todos os cenários 1–28 verdes.

---

## Phase 6: Telas (US1–US3)

- [X] T022 [P] [US1] `frontend/apps/internal/src/lib/agenda.ts` (`:435-439`): `deletion_request` com `alcance?`,
      `requested_by?`, `requested_by_id?`, `reason?`, `devolucao?`, `venda_nova?` opcionais; `pedido_bloqueado?`,
      `pedido_da_venda?`
- [X] T023 [US1] `frontend/apps/internal/src/lib/eventOps.ts` (`:441-471`): `usePedirCancelamento`/`useRecusarPedido`
      no caminho novo; `setQueryData` só com o detalhe na mão (molde `:19`, `:45`; resposta sem `event` →
      `invalidateQueries`); invalida `["cancelamentos"]`, `["agenda"]`, `["agenda-dia"]`, as notificações e a faixa
      (`invalidarSumidosGoogle`, `lib/sumidosGoogle.ts:66-68`); a união `CodigoRecusaPedido`; `pedido_pendente` e
      `sem_pedido` recarregam o detalhe e anunciam (o `cancelado` já é do `aoRecusarMutacao`, `main.tsx:16-27`)
- [X] T024 [US1] `git mv components/EventDetail/SolicitarExclusaoDialog.tsx components/EventDetail/PedirCancelamentoDialog.tsx`:
      motivo em `textarea`; Tudo/Parte/Nada sem opção marcada; valor (`MoneyInput`) em Parte; nome e PIX em Tudo e
      Parte; num dia só, só Parte/Nada e o novo valor da venda; o alcance no 1º dia com outro dia vivo (escolha sem
      marcar, "Todos os N dias" / "Só este dia — a venda passa para o dia dd/mm", N e o dia seguinte do bloco `group`,
      `escolha_do_alcance` do detalhe — o servidor diz N e o próximo dia, a tela não calcula); outro dia: "vale só
      para ele"; venda virtual: só o motivo; "o que está em jogo" com
      venda e recebido que a tela já tem (sem número de escalados — esse o servidor conta e vai no aviso) e as linhas do
      que o cancelamento faz (e-mail aos escalados, multa decidida pelo Superadmin, o Casting tira e avisa, ensaio cai
      junto); "Depois de enviado, só o Superadmin fecha o pedido"; botão só com tudo preenchido; erros do servidor no
      campo; 375 px sem rolagem lateral
- [X] T025 [US2] `components/EventDetail/EventHeader.tsx`: o item do menu (`:363-373`) "Solicitar cancelamento" com o
      `title` honesto, desabilitado com pedido pendente ("Pedido de <nome> aguardando o Superadmin") ou com
      `pedido_bloqueado` (a frase); o quadro (`:462-495`): "Cancelamento pedido — aguardando o Superadmin", data, alcance;
      motivo, autor e devolução só quando vierem (fim do "Sem motivo informado.", `:466`); para o autor, "Se a cliente
      voltar atrás, avise o Superadmin — só ele fecha o pedido"; no satélite que herda, "pedido feito no 1º dia da
      venda" com link
- [X] T026 [US3] `components/EventDetail/EventHeader.tsx`: "Recusar pedido" (`:482-491`) por um diálogo de confirmação
      com motivo opcional; "Analisar e decidir" (`:474-481`) passa o pedido ao `ExcluirEventoDialog` (`:522-527`)
- [X] T027 [US3] `components/EventDetail/ExcluirEventoDialog.tsx`: prop opcional `pedido` mostrada depois de
      `ResumoImpacto` (`:517`), só leitura, sem copiar (motivo, alcance, devolução completa); o diálogo continua abrindo
      vazio (`:177-186`, `:207-223`); o pedido aparece sempre que o detalhe trouxer `deletion_request`, também quando o
      diálogo abre pelo menu "Excluir ou cancelar"; valores por `formatBRL` (`@manto/money`); o texto "Aparece para quem
      abre o evento." (`:589`) passa a dizer a régua da 1c-Q9
- [X] T028 [P] [US2] `components/FaixaSumidosGoogle.tsx` e `lib/sumidosGoogle.ts`: tipo com `pedidos?` (`:15-22`); a
      segunda frase na mesma linha de 40 px (`:77`, `:82-118`), cada uma com o seu botão (`aria-expanded`,
      `aria-controls`), o seu `aberto`/`ref`/lista (`:31-34`, `:123-160`); 1 pedido → link ao evento, N → lista com
      links; `visivel`/`useFaixaSumidosVisivel` por `total > 0 || pedidos.total > 0` (`:36-41`, `sumidosGoogle.ts:54-63`);
      frases curtas em 375 px
- [X] T029 [P] [US2] `components/SeloSituacao.tsx` (`:32`, `:37-55`): o ramo `exclusao_solicitada` — badge neutra
      "Cancelamento pedido", tooltip "Cancelamento pedido em dd/mm/aaaa" — e só "Cancelamento pedido" quando vier sem
      data (as listas de `event_situacao` — ficha da cliente, formulários, figurino, tags 3D — mandam só o código); `CalendarGrid.tsx:78-82` e
      `DayTimelineView.tsx:124-127` com o tooltip do pedido no chip
- [X] T030 [P] [US3] `pages/EventosCancelamentosPage.tsx`: título "Cancelamentos" (`:158`), a tabela "Aguardando
      decisão" (`:174-228`) com alcance e devolução (corte pelo que vier) e o link "Decidir" (`:217-219`);
      `lib/navigation.tsx` — as duas entradas (`:388-396`, `:504-513`) "Cancelamentos"
- [X] T031 [P] [US3] `components/notificacoes/NotificacaoItem.tsx` (`:7-16`): ícones dos dois kinds
- [X] T032 Typecheck (`cd frontend && npm run typecheck`); commit `feat(315): telas — pedir, o quadro, a recusa, a faixa,
      o selo e a fila`

---

## Phase 7: Polimento

- [ ] T033 Rodada inteira do `verify_315.py` duas vezes seguidas; limpeza com zero sobra
- [ ] T034 [P] Regressão (a lista da T003) e `ruff check` nos tocados contra HEAD — nota: o cenário 12 do
      `verify_303` (`:2374-2377`, `:2582`) passa a gerar `evento.pedido_cancelamento` aos Superadmins do `manto_local`;
      conferir que a limpeza dele (por `entity_type`, `:967`) os leva
- [X] T035 Tela aberta (skill `manto-conferir-tela`) pela lista do `quickstart.md` §3 — interno (desktop e 375 px) e
      portal (375×812), com o Google dublado
      — **feito 22/10** (Flask em 127.0.0.1:5011 com o Google dublado, Vite em `mp315.localhost:5193`, semente descartável
      já limpa): menu e diálogo no 1º dia de uma venda de 3 dias (alcance com "a venda passa para o dia 11/04", Tudo some
      em "só este dia"), envio, o quadro com a nota do autor, a faixa dourada (1 → link; 2 → "2 pedidos de cancel." em
      375 px), o selo neutro na Lista, a página "Cancelamentos" com alcance e devolução, o quadro só leitura no diálogo de
      cancelar (motivo do cancelamento vazio), "Recusar pedido" com motivo e a resposta no sino do Comercial; 375 px sem
      rolagem lateral (diálogo 343 px). **O portal não foi aberto**: a tela não mudou (o `em_confirmacao` já é
      desenhado desde a 303) e o cenário 14 do verify cobre o dado
- [ ] T036 [P] `docs/01` (cabeçalho e head; §2.2 as duas colunas; §3.3 os endpoints e o alias; §3.13.5 os dois kinds;
      §3.15 o `em_confirmacao`; o contrato da faixa; §4.3 RBAC), `docs/02` (menu, quadro, diálogos, faixa, selo, página
      "Cancelamentos", sino, portal), `docs/04` (fluxo do pedido; as invariantes da spec), `docs/05` (quitar a parte da
      224 da dívida 76; registrar o alias a remover)
- [ ] T037 `docs/03`: entrada nova no topo + linha no índice (a reconferência; o pedido do 1350; as premissas da
      Session)
- [ ] T038 `/speckit-converge` e, por achado confirmado, cenário vermelho no verify antes da correção
- [ ] T039 Pré-merge: `main` do dia na branch, rodada inteira e regressão de novo; `git status` limpo; merge e push
      **só quando o dono pedir**, à noite; depois do push, a sonda: um `/api/` com JSON e o `GET
      /api/events/sumidos-google` com a chave `pedidos` trazendo o 1350 (SC-006)
      — **cadeia de migrations**: a 310 (`e8b4a1c7d310`, pronta e não publicada) também desce de `c5d2f7a9e306`;
      quem entrar por último na `main` aponta o `down_revision` para a outra (senão o `flask db upgrade` do start acha
      dois heads e a produção não sobe). No `manto_local` as colunas da 315 entraram à mão (o banco está na 310)

---

## Dependências e ordem

- Setup (T001–T003) → Foundational (T004–T005) → US1 → US2 → US3 → Telas → Polimento.
- US2 depende da US1 (lê as cinco colunas); US3 depende da US1 (fecha o que foi gravado) e usa o serializador da US2
  na resposta.
- As telas dependem das chaves do servidor (fases 3–5); cada arquivo é independente.

## Paralelismo

- US1: T006 e T007 em paralelo com o começo de T008 (arquivos diferentes); T009 depois de T008.
- US2: T014, T015 e T016 em paralelo depois de T012.
- Telas: T022, T028, T029, T030, T031 em paralelo; T025/T026 (mesmo arquivo) sequenciais; T027 depois de T026.

## Cenários por fase (esperado ao fechar)

| Fase | Verdes | Vermelhos |
|---|---|---|
| Foundational (T005, contra o código de hoje) | 27, 28 | 1–26 |
| US1 | + 1–5, 7–9, 16, 17, 26 | 6, 10–15, 18–25 |
| US2 | + 6, 10–12, 14, 15 | 13, 18–25 |
| US3 | todos | — |

O tasks reagrupa os cenários da spec de propósito (spec: H1 = 1–9, H2 = 10–17, H3 = 18–28): cada cenário fica verde na
fase que constrói o que ele exige.

## Estratégia

Uma entrega só (a noite do pedido), com uma migration aditiva, num push à noite quando o dono pedir. MVP = US1 + US3
(pedir e decidir); a US2 entra no mesmo deploy, porque sem o corte da Q6 o pedido passaria a expor o motivo da cliente a
toda a equipe (hoje ele já sai sem corte, com zero uso — com a porta aberta, vira vazamento real).

---

## Phase 8: Convergence

Converge de 22/10 (duas leituras independentes — servidor e telas — conferidas contra o código). Por achado, cenário
vermelho no `verify_315.py` antes da correção quando o achado é do servidor: cenários 29–35 (bloco C), vermelhos em
`efbb8a00` e verdes depois (35/35). T051 sem cenário (quatro listas de setup pesado); as telas, por typecheck.

- [X] T040 Contar os escalados do aviso sem a vaga automática do técnico de som em SHOW (`solicitacao_ops.solicitar` → `elenco_dos_dias` conta o talento 42 / `SOUND_TECH_CHARACTER`; molde `sumico_ops.preso_ao_evento:189-197`) per FR-008 (contradicts)
- [X] T041 Dizer "sem devolução informada" no quadro e na fila quando o pedido (de antes do deploy ou pelo caminho velho) não traz devolução e a venda não é virtual — o servidor diz (`serializar_para`), a tela mostra (`QuadroDoPedido.tsx`, `EventosCancelamentosPage.tsx`) per FR-026 (missing)
- [X] T042 Faixa: "1 pedido de cancelamento aguarda decisão" / "N pedidos de cancelamento aguardam decisão", na faixa vermelha (`FaixaSumidosGoogle.tsx`) per FR-012 (contradicts)
- [X] T043 Mostrar o alcance também no "todos" ("todos os N dias da venda") no quadro, no diálogo de cancelar e na fila — texto pronto do servidor (`serializar_para`, a régua de `_texto_do_alcance`) per FR-010/FR-018/FR-024 (partial)
- [X] T044 Aviso do pedido feito num outro dia da venda: venda e recebido do 1º dia, nunca "sem venda" (`notificar_pedido_cancelamento`, `preso_ao_evento` do satélite) per FR-008 (partial)
- [X] T045 409 `cache_pago` do "todos": `dias` como `_evento_curto` (id, título, data) e a mensagem dizendo os dias, como o cancelar da 306 per FR-005 (partial)
- [X] T046 Pedir ou recusar num evento excluído no meio do caminho: 404 claro em vez de 500 (`refresh` de linha apagada em `solicitar`/`recusar`) per FR-022 (partial)
- [X] T047 `title` do item do menu: "Pede ao Superadmin que cancele este evento — ele recebe o aviso no sino" (`EventHeader.tsx`) per FR-001 (partial)
- [X] T048 Diálogo de pedir: dizer o que falta ao lado do "Enviar pedido" desabilitado (`PedirCancelamentoDialog.tsx`) per US1/AC3 (partial)
- [X] T049 409 de estado: `pedido_pendente` fecha o diálogo e anuncia no cabeçalho; `sem_pedido` anuncia "Este pedido já foi decidido" (`PedirCancelamentoDialog.tsx`, `EventHeader.tsx`) per plan V/T023 (partial)
- [X] T050 Excluir recarrega o sino e a fila de Cancelamentos (`useDeleteEvent`, `lib/eventOps.ts`) per FR-021 (partial)
- [X] T051 `situacao_desde` ao lado da `situacao` nas listas que já mostram o selo (`clientes_read.py:109`, `formularios_admin_read.py:74`, `figurino/producao_ops.py:554`, `impressoes3d/nfc_ops.py:374`) e as telas passam a data ao `SeloSituacao` per FR-013 (partial)
- [X] T052 Excluir usuário com pedido pendente: zerar o `deletion_requested_by_id` em vez de estourar (`admin/user_ops.delete_user`) per data-model "autor apagado" (partial)
- [X] T053 Comentários com o vocabulário velho ("exclusão solicitada", "pedido de exclusão") em `lib/agenda.ts:8-9`, `EventHeader.tsx:467`, `lib/eventOps.ts:92` per FR-024 (partial)
