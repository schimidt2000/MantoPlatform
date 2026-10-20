---
description: "Tasks da feature 312 — o cancelado sai de toda lista"
---
# Tasks: O cancelado sai de toda lista e só se vê onde se trata do cancelamento

**Input**: artefatos em `/specs/312-cancelado-fora-das-listas/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/api.md,
pesquisa/reconferencia-2026-10-20.md (linhas do HEAD `5c298ac5`; conferir antes de editar — a branch anda)

**Verificação (Princípio VIII)**: `specs/312-cancelado-fora-das-listas/verify_312.py`, na Foundational, rodado
vermelho contra a `main` antes de qualquer linha do núcleo. Cada fase fecha com a rodada inteira, o `typecheck` e
o `ruff check` nos tocados. Sem migration.

**Regras de trabalho desta feature** (da 306, valem aqui):
- não editar `app/` com rodada do verify em andamento; antes de confiar numa rodada vermelha, procurar `verify_*`
  de outro worktree no mesmo `manto_local`;
- toda constante de mensagem mora na classe de erro ou em `app/constants.py`, uma vez;
- commit por caminho, nunca `git add -A`; mensagem por arquivo (`git commit -F`).

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [ ] T001 Conferir o ambiente: `.specify/feature.json` → `specs/312-cancelado-fora-das-listas`; `DATABASE_URL` de
      `C:\Users\schim\Desktop\Manto_Platform\.local-db-url`; venv com as dependências do `requirements.txt`;
      `alembic heads` do `manto_local` = head da `main` (sem migration nova)
- [ ] T002 [P] Ler `specs/306-dinheiro-do-cancelamento/verify_306.py` nos ajudantes listados na reconferência
      (§"Verify da 306 para reusar") e decidir o que importar dele × copiar (importar mantém uma fonte; o verify da
      306 é módulo com `if __name__ == "__main__"`)

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [ ] T003 **`specs/312-cancelado-fora-das-listas/verify_312.py`** — esqueleto no molde do `verify_306.py`:
      guarda de ambiente (banco em `localhost`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`), disjuntor de rede,
      `_send_falso` como dublê de e-mail, `GoogleFalso`, `cenario(bloco, nome, fn)`, `_no_banco` por conexão
      separada, `_sob_mutacao` (sonda limpa antes da mutada), `--so=`, `--limpar`, `--semear-tela`,
      `--limpar-tela`, `limpar()` no `finally`; PREFIX `__v312_`, marcador "[TESTE verify 312] pode apagar"
- [ ] T004 `verify_312.py` — semente comum: usuários de papel único (SUPERADMIN, COMERCIAL dona da venda, COMERCIAL
      2, FINANCEIRO, CASTING ×2, FIGURINO, ENSAIO, REVENDEDOR_EDUCAMANTO), talentos e cliente descartáveis, o
      exemplo-padrão (venda 2.000, pago 1.000, devolução 600, retido 400, comissão 18, BV 40) com dois escalados
      (aceito, pendente), um que recusou e a presença, cancelado pelo `POST …/cancelar` da 306; evento vivo de
      controle no mesmo dia; marcado (303) e com pedido de exclusão; "cancelado legado" (UPDATE de `cancelled_at`
      sem `event_cancellations`, conexão separada) para o R1; ensaio legado cancelado por UPDATE
- [ ] T005 `verify_312.py` — cenários 1–7 (História 1) com controle vivo em cada consulta e prova por mutação
- [ ] T006 `verify_312.py` — cenários 8–14 e 9b (História 2): Q9 por papel e "Ver como"; trava em uma rota de
      cada linha como SUPERADMIN real (API e Jinja, "Imprimir fichas"); portas livres; recusas Q5 e Q2; flags;
      controle com pedido pendente e marcado. 9b: percorrer `app.url_map` (métodos de escrita com
      `<event_id>`, `<role_id>`, `<gift_id>`, `<observation_id>`, `<ensaio_id>`) e exigir que cada rota esteja
      numa das duas listas do verify ("trava" ou "livre")
- [ ] T007 `verify_312.py` — cenário 15 (História 3): pendência, gate do `assign`, 409 com talento, sino lido,
      zero e-mail no cancelado e um no vivo
- [ ] T008 `verify_312.py` — cenários 16–17 (História 4): página como FINANCEIRO, filtros, 400, legado; RBAC
- [ ] T009 `verify_312.py` — cenários 18–19 (História 5): card do pipeline e da DRE, escopo, corte Q1, retido =
      KPI = linha da DRE, mês vazio, "Tudo" devolvido
- [ ] T010 `verify_312.py` — cenários 20–23 (História 6, regressão, limpeza): `event_situacao` nas ligadas, gasto
      com o mesmo evento e gasto novo por chamada direta, portal, payload igual à `main` num mês sem cancelado,
      limpeza com zero sobra
- [ ] T011 Rodar o `verify_312.py` contra a `main` (antes de qualquer código) e guardar a saída em
      `specs/312-cancelado-fora-das-listas/verify_312_primeira_falha.txt`. Esperado: 22 e 23 verdes; 1–21 e 9b
      vermelhos **pelo motivo certo** (o cancelado vem; a escrita grava; o motivo vem; o FINANCEIRO recebe 403;
      falta `cancelamentos`). Vermelho por erro do harness não conta — corrigir o harness antes de seguir
- [ ] T012 Núcleo em `app/calendar/cancel_ops.py`, sem chamadores: `EventoSomenteConsultaError` (409,
      `CODIGO_EVENTO_CANCELADO`, "Este evento foi cancelado — a tela fica só para consulta.") e
      `exigir_evento_vivo(event)`; `EventoCanceladoVinculoError` e `recusar_se_cancelado_para_ligar(event, *,
      campo=None, mensagem)` (400 com `fields` quando há campo, 409 sem); docstrings com o porquê (research R2, R3)
- [ ] T013 `app/api_utils.py`: `json_recusa_do_cancelado(exc)` (a tradução que hoje é
      `_recusa_do_cancelado`, `agenda_write.py:121-125`); `_recusa_do_cancelado` passa a delegar a ela. Rodar o
      `verify_306.py` (base 67/69) e o `verify_306b.py` (8/8) para provar que nada mudou

**Checkpoint**: verify inteiro escrito e vermelho pelo motivo certo; `verify_306`/`306b` na base.

---

## Phase 3: História 1 — O cancelado some de toda lista (P1) 🎯 MVP

**Objetivo**: FR-001–FR-010. **Teste independente**: cenários 1–7 verdes; 22 continua verde.

- [ ] T014 [P] [US1] Dia API: `cancelled_at.is_(None)` na consulta de `app/api/agenda.py:91-96`
- [ ] T015 [P] [US1] Dia Jinja: o mesmo filtro em `agenda_day`, `app/calendar/routes.py:533-538`
- [ ] T016 [US1] Busca: filtro antes do limite em `search_events`, `app/calendar/event_ops.py:1636-1694` (vale para
      `agenda.py:64` e `grupo/candidatos`, `agenda_write.py:2646`)
- [ ] T017 [P] [US1] Seletor por data: filtro em `search_events_by_date`, `app/gastos/gastos_ops.py:205-219`
- [ ] T018 [P] [US1] Formulário automático: filtro em `_real_event_candidates`,
      `app/formularios/formularios_ops.py:849-859`; lista Jinja de shows candidatos do `link-parent`
      (`routes.py:~1702`)
- [ ] T019 [P] [US1] Ficha do talento: filtro em `hist_q`, `app/talents/talent_ops.py:225-235` (os quatro números
      de `:286-317` saem da mesma lista — conferir)
- [ ] T020 [US1] Ficha da cliente: `app/api/clientes_read.py:80-93` — lista e `event_count` sem o cancelado, sai
      `"cancelado": e.is_cancelled` (`:87-88`), nova chave `cancelamentos: {quantidade, retido}` por
      `resumos_cancelados` em lote (research R6); `form_history[].event_situacao` (`:96-104`)
- [ ] T021 [P] [US1] Fila 3D e pendências: filtros em `list_print_queue` e `list_pending_events`,
      `app/impressoes3d/impressoes3d_ops.py:428-431`, `:468-472`
- [ ] T022 [P] [US1] Conflito de agenda: filtro em `_talent_time_conflict` (`app/calendar/routes.py:2104-2111`) e
      na disponibilidade do `event_detail` (`:1759-1767`)
- [ ] T023 [US1] Grupo: `_group_block` (`app/api/agenda_read.py:715-724`) usa `group_ops.dias_vivos` no principal
      vivo; no principal cancelado fica como está. `group_label` só com vivos em `app/financeiro/vendas_ops.py:353`
      e `app/api/financeiro_read.py:416`
- [ ] T024 [P] [US1] Ensaio legado: `ensaios[]` sem cancelado (`app/api/agenda_read.py:890-899`) e
      "agendado/falta agendar" (`app/calendar/dashboard_service.py:193-194`)
- [ ] T025 [US1] Tela — `frontend/apps/internal/src/pages/ClientDetailPage.tsx:183-208`: sai o ramo do cancelado;
      sublinha "inclui R$ X retidos de N cancelamento(s)" quando `cancelamentos.quantidade > 0`; tipo
      `ClientDetail.cancelamentos?` e `event_situacao?` em `frontend/apps/internal/src/lib/clientes.ts`
- [ ] T026 [US1] Rodada: cenários 1–7 e 22 verdes; `npm run typecheck`; `ruff check` nos tocados; commit
      `feat(312): história 1 — o cancelado sai de toda lista`

---

## Phase 4: História 2 — A tela do cancelado só para consulta; motivo só para quem trata (P1)

**Objetivo**: FR-011–FR-022. **Teste independente**: cenários 8–14 e 9b verdes.

- [ ] T027 [US2] Q9 no detalhe: `cancellation_reason` e `cancelled_by` só com `show_comercial`
      (`app/api/agenda_read.py:830-831`)
- [ ] T028 [US2] Flags: `flags_do_detalhe` (`app/api/agenda_read.py:207-228`) — `somente_consulta: true` e
      `can_edit_event`, `can_edit_core`, `can_confirm`, `can_group`, `can_manage_3d` falsas no cancelado
- [ ] T029 [US2] Ajudante `_trava_do_cancelado(event)` em `app/api/agenda_write.py` (irmão de `_recusa_se_cancelado`,
      `:132-145`) e a chamada, depois do 404/403, em: `PATCH /events/<id>` (`:1246`, todo corpo), `…/basico`
      (`:1346`), confirm (`:429`), logistics (`:445`), observações (`:476`, `:540`), clients (`:1492`), contratos
      (`:1945`, `:1975`, `:1994`), travel-estimate (`:2314`), materiais (`:2346`, `:2388`), presença (`:2537`),
      renomear grupo (`:2797`)
- [ ] T030 [US2] A trava nas vagas: `DELETE /roles/<id>` (`:266`), figurino feito (`:305`, `:2294`), transporte
      (`:326`, `:365`), dismiss/restore (`:390`, `:409`), payment-status (`:2243`), figurino-sheet (`:2267`)
- [ ] T031 [P] [US2] A trava no `PATCH` do presente 3D (`app/api/impressoes3d_write.py:154`)
- [ ] T032 [US2] Recusas Q5 no núcleo, antes de qualquer e-mail: `assign_role` com talento
      (`app/calendar/casting_ops.py:67`), `add_role` com talento (`:421`), `send_invite` (`:501`),
      `convidar_recem_escalados` (`:525`); tradução 409 nas rotas `:206`, `:238`, `:288` e no `PATCH /events/<id>`
- [ ] T033 [US2] Recusas Q2 de ensaio: `create_ensaio` (`app/calendar/event_ops.py:1761`, antes do Google) → 409 na
      rota `:2417`; `link_ensaio_to_show` (`:1871`) → 400 `fields.parent_event_id` na rota `:2513`
- [ ] T034 [P] [US2] Tag NFC: `update_tag` (`app/impressoes3d/nfc_ops.py:289`) recusa vínculo novo a cancelado →
      400 `fields.event_id` (`app/api/nfc_write.py:52`); o mesmo id e `null` passam
- [ ] T035 [P] [US2] Presente 3D novo: `add_event_gift` (`app/impressoes3d/impressoes3d_ops.py:319`) → 409 na rota
      `app/api/impressoes3d_write.py:126`
- [ ] T036 [P] [US2] Formulário: `apply_event_link` (`app/formularios/formularios_ops.py:465`) recusa ligar a
      cancelado → 409 em `PATCH …/form-response` (`agenda_write.py:1515`), `vincular-evento`
      (`app/api/formularios_admin_write.py:220`) e na edição em bloco; desligar passa
- [ ] T037 [P] [US2] Pedido de figurino: `_resolver_evento` (`app/figurino/producao_ops.py:595`) recusa vínculo
      novo → 400 `fields.event_id` (`app/api/figurino_producao_write.py:78`, `:111`, `:156`)
- [ ] T038 [P] [US2] Avaliação: `ensure_feedback_token` (`app/calendar/event_ops.py:1527`) → 409 na rota `:2563`;
      `GET`/`POST /api/avaliar/<token>` (`app/api/feedback_write.py:45`, `:64`) → 410 sem título nem data
- [ ] T039 [US2] Jinja: no despachante `event_detail` (`app/calendar/routes.py:1658`, `_EVENT_ACTIONS` `:1621`) uma
      checagem antes do `handler` para todas as ações no cancelado (`flash` + `redirect`); a mesma linha em
      observações (`:4504`, `:4546`), materiais (`:4296-4372`), dismiss/restore (`:4607`, `:4629`),
      `create-ensaio` (`:2615`), `link-parent` (`:2787`), `assign_casting` (`:1622` se fora do despachante) e
      "Imprimir fichas" (`app/figurino/routes.py:36`)
- [ ] T040 [US2] Tela — `frontend/apps/internal/src/components/EventDetail/`: com `flags.somente_consulta`,
      esconder o que grava em `EventHeader.tsx` (confirmar `:320`, "Pedir feedback" `:324`), `ResumoSection.tsx`
      (`:267`, `:275`), `ComercialSection.tsx` (Clientes `:504`, Pré-contrato `:917` — fica o desligar, renomear
      grupo `~:1177`), `FinanceiroSection.tsx` (contratos `:24`, `:72-100`), `LogisticaSection.tsx` (`:56`,
      `:232`, `:250`, `:381`), `ObservacoesSection.tsx` (`:205-221`), `FigurinoSection.tsx` (`:107`, imprimir
      `:163-170`), `EnsaioSection.tsx` (`:148`, `:340`, `:374`), `Presente3DSection.tsx` (`:106`, `:126` — fica o
      soltar), `FeedbackSection.tsx` (`:84-85`); `CastingSection.tsx` fica para a T049
- [ ] T041 [US2] Painéis de venda para quem não é Superadmin: a frase "Evento cancelado: só o Superadmin altera os
      dados de venda." onde os controles somem (`ComercialSection.tsx:980-983`, `ColecoesComerciaisPanel.tsx:69-73`,
      `FinanceiroSection.tsx:335`, `:423`, `:579`)
- [ ] T042 [US2] Caixa do cancelado (`EventHeader.tsx:409-430`): frase "Saiu da agenda e das listas do sistema;
      fica na página de Cancelamentos e no card 'Cancelamentos do período'. A tela fica só para consulta; só os
      dados de venda continuam editáveis, pelo Superadmin."; sem motivo do servidor → "Evento cancelado em DD/MM",
      sem linha (some o "Sem motivo registrado." para quem não pode ver); "Editar motivo" (306b) intocado
- [ ] T043 [US2] Recarregar ao receber `cancelado`: utilitário em `frontend/apps/internal/src/lib/eventOps.ts`
      (invalida `["event", id]`) no `onError` das mutações da tela; `EnsaioSection.tsx` passa a mostrar
      `vincular.error?.message`
- [ ] T044 [P] [US2] Avaliação pública: `frontend/apps/public/src/pages/AvaliarPage.tsx` mostra "Este evento foi
      cancelado — não há avaliação a fazer." no 410, sem formulário
- [ ] T045 [US2] Rodada: cenários 8–14 e 9b verdes (9b lista toda rota de escrita; nenhuma sem classificação);
      `verify_306`/`306b` na base; typecheck; ruff; commit `feat(312): história 2 — a tela do cancelado só para
      consulta e o motivo só para quem trata dele`

---

## Phase 5: História 3 — O Casting tira e avisa (P2)

**Objetivo**: FR-023–FR-026. **Teste independente**: cenário 15 verde.

- [ ] T046 [US3] `cancel_ops`: o predicado "a avisar" pela régua de `elenco_do_ato` sobre as vagas de hoje, em lote
      para todos os cancelados futuros (research R5)
- [ ] T047 [US3] `casting.cancelados_a_avisar` em `compute_casting_tasks` (`app/calendar/dashboard_service.py:53`),
      itens no molde de `serialize_unconfirmed_ref` (`:277-295`), corte `dashboard_cutoff`, ordem pela data
- [ ] T048 [US3] `api_assign_role` (`app/api/agenda_write.py:206-236`) no cancelado: `_can_casting()` (`:59`) com
      403 "Evento cancelado: quem tira da escala é o Casting."; só `talent_id` nulo sem cachê nem transporte; o
      resto → trava; depois da remoção, sem ninguém a avisar no dia → `marcar_lidas_por_entidade("calendar_event",
      dia.id, KIND_EVENTO_CANCELADO_ESCALA)` (`app/notificacoes/notificacoes_ops.py:458`) na mesma transação
- [ ] T049 [US3] Tela: `CastingSection.tsx` (`:634`, `RoleCard :318-440`, `AddRoleForm :684/:695`) no cancelado —
      só "Tirar da escala" e o WhatsApp (`:420`) para `show_casting`, com a frase "Evento cancelado: exclua os
      escalados e avise cada um pelo WhatsApp."; os outros só leem
- [ ] T050 [US3] Home: bloco "Eventos cancelados — excluir e avisar" em
      `frontend/apps/internal/src/pages/DashboardPage.tsx` (molde `UnconfirmedRow`, `:153`), agrupado por evento,
      com "Avisar no WhatsApp" (mensagem da FR-026; sem WhatsApp → "sem WhatsApp no cadastro") e "Tirar da escala"
      com confirmação; tipo opcional irmão de `UnconfirmedInviteRef` em `frontend/apps/internal/src/lib/types.ts:37`
- [ ] T051 [US3] Rodada: cenário 15 verde; typecheck; ruff; commit `feat(312): história 3 — o Casting tira os
      escalados do cancelado e avisa`

---

## Phase 6: História 4 — A página de Cancelamentos (P2)

**Objetivo**: FR-027–FR-031. **Teste independente**: cenários 16–17 verdes.

- [ ] T052 [US4] Gate `_can_read_cancelamentos()` (SUPERADMIN ou FINANCEIRO pelo papel real) em
      `app/api/agenda_write.py` ao lado de `_can_delete` (`:114-118`, intocado); a rota `:870-881` passa a usá-lo;
      validação de `mes` (`AAAA-MM`) e `devolucao` com 400 `fields`
- [ ] T053 [US4] `listar_cancelamentos(*, flags, mes=None, devolucao=None)` (`app/calendar/cancel_ops.py:3397-3468`):
      mês em São Paulo sem limite; `EXISTS`/`NOT EXISTS` por `filtro_devolucao` (`:233-243`) antes do limite;
      `total_retido`, `total_retido_escopo`, `filtros`; sai `_devolucao` (`:3420-3434`)
- [ ] T054 [US4] Tela `frontend/apps/internal/src/pages/EventosCancelamentosPage.tsx`: filtros na URL (inválido
      volta ao padrão), Buscar (título ou motivo), colunas Venda · Pago · Devoluções · Retido · Comissão · BV ·
      Imposto, total no cabeçalho ("nos N listados" sem mês), vazio com "Limpar filtros", erro com a mensagem do
      servidor (`:58-62`), dia cortado e "a venda passou para DD/MM" (`resumo.venda_passou_para`); tira a leitura
      do `devolucao` legado (`:148-149`, `:229`)
- [ ] T055 [US4] `useCancelamentos({mes, devolucao})` com os dois na chave (`frontend/apps/internal/src/lib/eventOps.ts:546-554`)
- [ ] T056 [US4] Menu: "Exclusões e cancelamentos" para FINANCEIRO, duplicado na seção Financeiro com `key` própria
      (`frontend/apps/internal/src/lib/navigation.tsx:493-503`); sai o comentário "única porta"
- [ ] T057 [US4] Rodada: cenários 16–17 verdes; typecheck; ruff; commit `feat(312): história 4 — a página de
      Cancelamentos para o Superadmin e o Financeiro`

---

## Phase 7: História 5 — O card "Cancelamentos do período" (P2)

**Objetivo**: FR-032–FR-035. **Teste independente**: cenários 18–19 verdes.

- [ ] T058 [US5] `painel_de_cancelamentos(inicio, fim, *, seller_id=None, educamanto_only=False, com_imposto)` em
      `app/calendar/cancel_ops.py` sobre `cancelados_do_periodo`/`totais_cancelamentos` (`:586`, `:627-655`),
      comissão pela regra do KPI com vendedor (`app/financeiro/vendas_ops.py:314-321`); itens com `event_date`,
      `seller_name`, `pago`, `devolvido`, `devolucao_a_pagar`, `comissao_retido`
- [ ] T059 [US5] DRE: `paineis.cancelamentos` (`app/api/financeiro_read.py:538-563`) passa a sair da função; os
      números de hoje iguais (cenário 19 compara com a `main` por `_sob_mutacao`)
- [ ] T060 [US5] Pipeline: `cancelamentos` sempre presente em `GET /api/vendas/pipeline`
      (`app/api/financeiro_read.py:122-183`, escopo de `:160-164`), imposto e efeito só com a flag de SA/FIN
- [ ] T061 [US5] Componente do card (no molde do card da loja, `VendasPipelinePage.tsx:325`) usado em
      `VendasPipelinePage.tsx` e em `FinanceiroDashboardPage.tsx` acima de "📋 Eventos no Período" (`:730`): só com
      `quantidade > 0`, números, lista com link de cada evento, "Ver na página de Cancelamentos" (`?mes=`) só para
      quem abre a página; tipo `CancelamentosDoPeriodo` (`frontend/apps/internal/src/lib/financeiro.ts:71-82`)
      reaproveitado e o do pipeline opcional
- [ ] T062 [US5] Rodada: cenários 18–19 verdes; typecheck; ruff; commit `feat(312): história 5 — o card
      "Cancelamentos do período"`

---

## Phase 8: História 6 — Selo nas coisas ligadas; portal (P3)

**Objetivo**: FR-036–FR-039. **Teste independente**: cenários 20–21 verdes.

- [ ] T063 [P] [US6] `event_situacao` em `serialize_tag` (`app/impressoes3d/nfc_ops.py:341-368`),
      `app/api/formularios_admin_read.py:89` e no pedido de figurino (`app/figurino/producao_ops.py:553`)
- [ ] T064 [US6] `SeloSituacao.tsx` (`frontend/apps/internal/src/components/SeloSituacao.tsx:24-30`) ganha o ramo
      `cancelado` (Badge vermelho "Cancelado", ícone `Ban`, compacto com `aria-label`); usado em Gastos Extras
      (`GastosExtrasPage.tsx:535`, pelo `event_cancelled`), `/3d/tags`, `FormulariosAdminPage.tsx:490`,
      `FigurinoProducaoListPage.tsx:497-499`, `FigurinoProducaoDetailPage.tsx:617-619` e no histórico de formulários
      da ficha da cliente; tipos opcionais em `lib/nfc.ts` e afins
- [ ] T065 [US6] Selects de Gastos Extras (`EventoVincular` `:88-113`, `EventoFields` `:244-275` de
      `GastosExtrasPage.tsx`): o evento atual como opção fixa quando não está na lista do dia
- [ ] T066 [P] [US6] Portal: `app/api/portal_figurino.py:36-39` recusa o cancelado com 400 "Este evento foi
      cancelado." depois do 403; `frontend/apps/portal/src/pages/PortalFigurinoPage.tsx:39-43` mostra a frase do
      servidor
- [ ] T067 [US6] Rodada: cenários 20–21 verdes; typecheck; ruff; commit `feat(312): história 6 — o selo nas coisas
      ligadas e o portal`

---

## Phase 9: Polimento

- [ ] T068 Rodada inteira 24/24 (com 9b) duas vezes seguidas; limpeza com zero sobra (cenário 23)
- [ ] T069 [P] Regressão: `verify_306.py` (base 67/69), `verify_306b.py`, `verify_303.py`; de `scripts/db/`:
      `verify_cancelamento_evento.py`, `verify_145_agenda_read.py` (escolhe o evento mais recente sem olhar
      cancelamento — anotar se falhar por isso), `verify_196_dashboard_comercial.py`, `verify_205.py`
- [ ] T070 Textos que mentem: docstring de `is_cancelled` (`app/models.py:401-409`), docstring de
      `_query_month_events` (`routes.py:192-194`), comentário "única porta" do menu
- [ ] T071 Tela aberta (skill `manto-conferir-tela`) pela lista do `quickstart.md` §3, com `--semear-tela` e
      `--limpar-tela`; portal e avaliação em 375×812 e 320–430 px; prints guardados no scratchpad
- [ ] T072 [P] `docs/00` §4 (FINANCEIRO lê Cancelamentos); `docs/01` §2.2, §3.3 (inventário de
      `/events/cancelamentos` — quita a 84), §3.4/§3.6–§3.8/§3.13, §4.3
- [ ] T073 [P] `docs/02`: agenda, Dashboard Comercial, DRE, página de Cancelamentos, fichas, Gastos Extras,
      seletores, Fila 3D, menu, tela do cancelado, Home do Casting, painel do grupo, portal, avaliação
- [ ] T074 [P] `docs/04` (invariante do cancelado e o fluxo "o Casting tira e avisa"); `docs/05` (riscar 74 e 84;
      registrar o que sobrar)
- [ ] T075 `docs/03`: entrada nova no topo + linha no índice (registrar que a frase da 306b "os demais veem o
      motivo" ficou superada pela Q9; a recontagem de 20/10; o 1358 legado)
- [ ] T076 `/speckit-converge` e, por achado confirmado, cenário vermelho no verify antes da correção
- [ ] T077 Pré-merge: rebase sobre a `main` do dia, rodada inteira e regressão de novo; `git status` limpo; merge e
      push **só quando o dono pedir**

---

## Dependências e ordem

- Setup → Foundational (T003–T013) → histórias.
- **H1** e **H2** (P1) são independentes entre si; H2 depende da T012/T013.
- **H3** usa a trava da H2 (o `assign` com talento cai nela) — depois da H2.
- **H4** e **H5** independentes entre si e de H1–H3.
- **H6** independente; a T064 usa o `event_situacao` da T063 e da T020.
- Polimento por último.

## Paralelismo

- Foundational: T005–T010 são o mesmo arquivo (sequenciais); T012 e T013 em paralelo depois da T011.
- H1: T014, T015, T017, T018, T019, T021, T022, T024 em paralelo (arquivos diferentes); T016, T020, T023, T025
  depois.
- H2: T031, T034–T038, T044 em paralelo; T029/T030/T032/T033/T039 mexem em `agenda_write.py`/`routes.py`/núcleos
  compartilhados — sequenciais.
- H6: T063 e T066 em paralelo.

## Cenários por fase (esperado ao fechar)

| Fase | Verdes | Vermelhos |
|---|---|---|
| Foundational (T011) | 22, 23 | 1–21, 9b |
| H1 | 1–7, 22, 23 | 8–21, 9b |
| H2 | 1–14, 9b, 22, 23 | 15–21 |
| H3 | + 15 | 16–21 |
| H4 | + 16, 17 | 18–21 |
| H5 | + 18, 19 | 20, 21 |
| H6 | todos (24/24) | — |

## Estratégia

MVP = H1 + H2 (os dois P1: some de toda lista; tela só consulta e motivo só para quem trata). H3–H6 entram no mesmo
deploy (um push só, quando o dono pedir); cada história fecha com commit próprio para o converge e o rollback
lerem a fronteira.
