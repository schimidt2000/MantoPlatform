# Reconferência do plano 1c contra a `main` de 20/10/2026 (`5c298ac5`)

O plano (`docs/backlog/1c-sinalizar-e-filtrar-cancelados.md`, untracked no checkout principal) foi escrito
contra `f6ad283` (01/10). Desde então subiram 305, 306, 306b, 307, 308, 309 e 311. Três leitores (só leitura)
conferiram em 20/10 cada fatia do plano contra o HEAD. Aqui fica o que mudou; as linhas são do HEAD `5c298ac5`.
O plano continua sendo a fonte do desenho; onde este arquivo diverge dele, vale este arquivo.

## Recontagem em produção (20/10, só leitura, SSH no `manto-backend`)

Script `ro_1c.py` (scratchpad da sessão), `psycopg2` com `readonly=True`.

- **2 cancelados, os dois com venda**: o 388 (R&I, 22/10, cancelado 20/10 09:39 pelo caminho da 306, devolução
  R$ 1.140 aprovada e não paga) e o **1358** (SHOW, 17/10, venda R$ 7.318, cancelado em **02/10** pelo caminho
  antigo da 224 — antes da 306, sem devolução lançada). Nenhum ensaio ou satélite cancelado.
- 1 evento marcado (303) e 1 pedido de exclusão (224).
- Papéis: ARTISTA_3D 1, CASTING 2, COMERCIAL 3, ENSAIO 2, FIGURINO 5, REVENDEDOR_EDUCAMANTO 2, SUPERADMIN 3.
  **FINANCEIRO continua com zero usuários.**
- Eventos vivos por mês: out/26 84, nov 45, dez 22, jan/27 2. Elenco futuro: 35 eventos, 113 escalações, 26
  convites pendentes. 17 ensaios futuros; 0 satélites futuros; 77 eventos futuros com venda; 2 pedidos de
  figurino abertos de evento futuro; 1 presente 3D aberto; 23 tags com evento.

Consequência: o 1358 é o caso real do "cancelado pela regra velha" (plano §4 item 9, "Erro"). A página de
Cancelamentos e o card têm de mostrá-lo sem quebrar — conferir no plan o que `resumo_cancelado` devolve para
ele (sem linha de congelamento da 306).

## Filtros de leitura

| Ponto | HEAD | Estado |
|---|---|---|
| Agenda Mês/Lista (`_query_month_events`, filtro `routes.py:204`; `agenda_read.py:128`) | — | já filtra (224) |
| Dia API `GET /api/agenda/day` | `app/api/agenda.py:80-100` (consulta `:91-96`) | **falta** |
| Dia Jinja `agenda_day` | `app/calendar/routes.py:524-538` | **falta** |
| Busca `search_events` (serve busca, `grupo/candidatos`, vínculo de ensaio, tag NFC) | `app/calendar/event_ops.py:1636-1694`; chamadores `agenda.py:64`, `agenda_write.py:2646` | **falta** |
| Seletor por data `search_events_by_date` (Gastos, pedido de figurino, formulário) | `app/gastos/gastos_ops.py:205-219` | **falta** |
| Ficha do talento (histórico e 4 números) | `app/talents/talent_ops.py:225-235`, `:286-317` | **falta** (intocada) |
| Ficha da cliente — lista | `app/api/clientes_read.py:80-93` (`"cancelado": e.is_cancelled` em `:87-88`), `client_ops.py:135-172` | **mudou (306)**: total com retido e `event_count` sem cancelado já existem, mas a 306 **manteve o cancelado na lista**, marcado (P-43), e `ClientDetailPage.tsx:183-208` desenha. A 1c tira da lista e manda `cancelamentos:{quantidade, retido}` |
| `list_clients` / `client_metrics` | `client_ops.py:121`, `:233` | já filtram (306) |
| `form_history[].event_situacao` na ficha da cliente | `clientes_read.py:96-104` | **falta** |
| Home: tarefas, convites, cobranças | `dashboard_service.py:37` (`not_cancelled`), `:188`, `:203`, `:223`; `invite_reminders.py:91`; `cobranca_ops.py:450` | já filtra (308 pôs `not_compromisso_interno` ao lado) |
| Home: "agendado/falta agendar" do ensaio | `dashboard_service.py:193-194` | falta — só legado (a 306 apaga o ensaio no ato, `cancel_ops.py:2220-2233`) |
| Performance da Home; `/admin/desempenho` | `dashboard_service.py:323-328`; `admin_config_read.py:155` | já filtram (306) |
| `ensaios[]` no detalhe do show | `agenda_read.py:890-899` | falta — só legado |
| Painel "Grupo comercial" do principal vivo | `agenda_read.py:690-733` (lista `:715-724`, `"cancelado": s.is_cancelled` em `:720-721`); `ComercialSection.tsx:1233-1234` (badge, esconde "Remover") | **mudou (306)**: o dia cancelado aparece marcado. A 1c tira do principal vivo; o campo e o badge viram código morto no vivo (no principal cancelado a lista continua) |
| Rótulo "(N eventos)" | `vendas_ops.py:353`, `financeiro_read.py:416` (`len(satellites)+1`) | **falta**; reusar `group_ops.dias_vivos` (`group_ops.py:119-125`) |
| Lista de vendas, tabela da DRE, DRE/Planilha Jinja, `/vendas/` Jinja | `vendas_ops.py:175`; `financeiro_read.py:240`; `financeiro/routes.py:301, :490, :734, :1529-1536` | já filtram (o `/vendas/` pela 306) |
| Fila 3D `list_print_queue`; pendências de presente `list_pending_events` | `impressoes3d_ops.py:413-441` (`:428-431`), `:448-476` (`:468-472`) | **falta**; dívida 74 aberta |
| Tag NFC `serialize_tag` (situação do evento) | `nfc_ops.py:341-368` | **falta** |
| Formulário automático `_real_event_candidates`; `formularios_admin_read` `event_situacao` | `formularios_ops.py:849-859`; `formularios_admin_read.py:89` | **falta** (o caminho da 298 já recusa, `destino_ops.py:273/:454`) |
| Conflito de agenda `_talent_time_conflict`; disponibilidade Jinja do `event_detail` | `routes.py:2084` (consulta `:2104-2111`); `routes.py:1759-1767` | **falta** (o gêmeo da API já filtra, `event_ops.py:1430`) |
| Portal: agenda, histórico, avaliação | `portal_ops.py:223, :355, :913`; `portal_rating_ops.py:124` | já filtra |
| Portal: ficha de figurino por link | `portal_ops.py:505-534`; `app/api/portal_figurino.py:36-39`; `PortalFigurinoPage.tsx:39-43` | **falta** |
| Calculadora "já na agenda"; histórico de orçamentos | `quote_ops.py:842`; `orcamento_read.py:229` | já filtram |

Nada novo da 305, 307, 308, 309 ou 311 lista ou deixa escolher evento. Os pickers continuam sendo
`useAgendaSearch` (AgendaSearchResults, `EnsaioSection:192`, `AssociarDialog:34`) e `useGastosEventos`
(GastosExtras `:103/:314`, FigurinoProducaoList `:134`, FormulariosAdmin `:481`).

**Fonte única de "cancelado"**: a coluna `CalendarEvent.cancelled_at` (`models.py:298`); `is_cancelled`
(`:401-409`, docstring reescrita pela 306 e ainda falsa enquanto o Dia e a busca mostram o cancelado);
`situacao`/`situacao_desde` (`:427-449`); `SITUACAO_CANCELADO` (`constants.py:616`). Não há predicado SQL
reutilizável — todo filtro é `cancelled_at.is_(None)` inline (o único nomeado é `_base_filters()["not_cancelled"]`,
local da Home). Precedente de predicado: `sumico_ops.filtro_marcados()` (`sumico_ops.py:160`).

**Reaproveitar da 306**: `group_ops.dias_vivos`; `CODIGO_EVENTO_CANCELADO = "cancelado"` (`constants.py:624`; o
`sumico_ops.CODIGO_CANCELADO`, `:650`, é homônimo de outro fluxo — o comentário `constants.py:619-622` manda não
comparar os dois); `group_ops.recusar_cancelado_no_grupo` (`:145-168`); a tradução `_recusa_do_cancelado` /
`_recusa_se_cancelado` (`agenda_write.py:121-145`); `cancel_ops.resumos_cancelados(ids)` (`:382`),
`cancelados_do_periodo` (`:586`), `totais_cancelamentos` (`:627-655`), `filtro_devolucao` (`:233-243`). Atenção:
`cancel_ops.recusar_se_cancelado` (`:2967`) **deixa passar o Superadmin** (é a regra dos dados de venda): não
serve como a trava geral da 1c; a tradução e o código servem.

## Recusas e trava da tela

Nenhum endpoint de escala, ensaio, NFC, 3D, formulário, avaliação ou figurino olha `cancelled_at` hoje.

| Ação | HEAD | Estado |
|---|---|---|
| Escalar/trocar talento | `POST /roles/<id>/assign` (`agenda_write.py:206`, gate `_can_edit_event` `:213`); Jinja `assign_casting` (`routes.py:1622`); núcleo `casting_ops.assign_role` (`:67`) — escalar novo **manda convite** (`~:223`), mudar cachê de quem aceitou manda "evento mudou" (`~:249`) | **falta** — risco vivo: hoje dá para re-escalar alguém num cancelado e sai convite por e-mail |
| Vaga com talento | `POST /events/<id>/roles` (`:238`); `casting_ops.add_role` (`:421`, convida `~:455`) | falta |
| Convidar | `POST /roles/<id>/invite` (`:288`); `send_invite` (`:501`) | falta |
| Tirar da escala (Q10) | `assign` (`:206`) | parcial: a 306 cala o e-mail de remoção no cancelado (`casting_ops.py:61-64`, usado `:160-168`); falta o gate `_can_casting` (`:59`), aceitar só talento vazio e marcar o sino lido (`marcar_lidas_por_entidade`, `notificacoes_ops.py:458`) |
| Remover vaga; resto da vaga | `DELETE /roles/<id>` (`:266`); figurino-done `:305, :2294`; transporte `:326, :365`; dismiss/restore `:390, :409` (Jinja `routes.py:4607, :4629`); payment-status `:2243`; figurino-sheet `:2267` | falta |
| Link de avaliação | `POST /events/<id>/feedback-link` (`:2563` → `ensure_feedback_token`, `event_ops.py:1527`); `GET/POST /api/avaliar/<token>` (`feedback_write.py:45, :64`); Jinja `feedback/routes.py:20` | falta |
| Pedido de figurino com vínculo novo | `figurino_producao_write.py:111` (POST), `:156` (PATCH), `:78` (solicitar-ficha); `producao_ops._resolver_evento` (`:595`) | falta |
| Agendar ensaio | `POST /events/<id>/ensaios` (`:2417`); Jinja `create-ensaio` (`routes.py:2615`); `create_ensaio` (`event_ops.py:1761`) escreve no Google antes de checar | falta |
| Vincular ensaio | `POST /ensaios/<id>/vincular` (`:2513`); Jinja `link-parent` (`routes.py:2787`, lista de shows candidatos `~:1702` traz cancelado); `link_ensaio_to_show` (`event_ops.py:1871`) | falta |
| Tag NFC vínculo novo | `PATCH /3d/nfc/<id>` (`nfc_write.py:52`); `update_tag` (`nfc_ops.py:289`) | falta |
| Presente 3D novo | `POST /events/<id>/3d-gifts` (`impressoes3d_write.py:126`); `add_event_gift` (`impressoes3d_ops.py:319`); o `PATCH` (`:154`) cai na trava | falta |
| Formulário | `PATCH /events/<id>/form-response` (`agenda_write.py:1515`); `vincular-evento` (`formularios_admin_write.py:220`); `apply_event_link` (`formularios_ops.py:465`) | falta |
| Grupo (agrupar/desagrupar) | `group_ops.validar_agrupamento` → `recusar_cancelado_no_grupo` (`group_ops.py:225`, `:145-168`) | já (306) |
| Renomear grupo | `PATCH /grupo` (`:2797`); `renomear_grupo` (`group_ops.py:355`) | falta |
| Dados de venda (comercial, parcelas, notas, acréscimos, comprovantes, reembolsos, devolução, multas) | `agenda_write.py:1423, :1929, :1722-1808, :1856-1861, :2032-2109, :2126, :2167, :709, :779` → `recusar_se_cancelado` → `pode_editar_venda_do_cancelado` (`cancel_ops.py:2967`, `:122`) | já (306); `DELETE /reimbursements` (`:2199`) não chama a regra mas já é só do Superadmin |
| Orçamento | `PATCH …/orcamento` (`:1587-1590`) | já (306), 409 para todos |
| Motivo do cancelamento | `PATCH /events/<id>/motivo-cancelamento` (`agenda_write.py:723-754`), `pode_editar_motivo_do_cancelado` (`cancel_ops.py:133`, Superadmin ou Comercial) | já (306b) — **fica livre da trava** (ordem do dono de 20/10) |
| Edição completa `PATCH /events/<id>` | `:1246` | parcial: a 306 recusa só se a venda mudar (`:1280`); título, data e elenco ainda gravam (o elenco passa por `convidar_recem_escalados`) |
| Resto da trava | `…/basico` `:1346`; confirm `:429`; logistics `:445`; observações `:476, :540` (Jinja `routes.py:4504, :4546`); clients `:1492`; contratos `:1945, :1975, :1994`; travel-estimate `:2314`; materiais `:2346, :2388` (Jinja `:4296-4372`); presença `:2537`; "Imprimir fichas" `figurino/routes.py:36` | falta; não existe `exigir_evento_vivo` |
| Despachante Jinja `event_detail` | `routes.py:1658`, `_EVENT_ACTIONS` `:1621`; a 306 recusa só 8 ações de dinheiro, **para todos, inclusive o Superadmin** (`:1646-1650`, `:1689-1698`) | parcial — a 1c pode recusar **todas** as ações no cancelado pelo Jinja |
| Excluir, cancelar de novo, devolver ao Google, pedir exclusão | `:616`; `cancel_ops.py:1541`; `:793`; `cancel_ops.py:3360` | já (306) |

Rotas Jinja fora do despachante que o plano não listava: observações, materiais, dismiss/restore, create e
link de ensaio.

**Tela (frontend)**: `flags_do_detalhe` (`agenda_read.py:207-228`) já liga `can_edit_venda_cancelado`
(Superadmin), `can_edit_pagamentos` e `can_edit_motivo_cancelado` (Superadmin ou Comercial). `_role_flags`
(`:155-204`) não olha o evento: `can_edit_event`, `can_edit_core`, `can_confirm`, `can_group`, `can_manage_3d`
seguem verdadeiras no cancelado; `somente_consulta` não existe. A 306 já esconde "Editar tudo"
(`EventHeader.tsx:336`), excluir/solicitar (`:350`) e os painéis de venda (`ComercialSection.tsx:980-983`, `:623`,
`:1119`; `ColecoesComerciaisPanel.tsx:69-73`; `FinanceiroSection.tsx:335, :423, :579`; `ResultadoCancelamento.tsx:53-59`)
— para quem não é Superadmin os controles somem **sem** a frase "só o Superadmin altera". Seguem gravando no
cancelado: confirmar e "Pedir feedback" (`EventHeader.tsx:320, :324`), `DadosEventoPanel` (`ResumoSection.tsx:267, :275`),
`ClientesPanel` (`ComercialSection.tsx:504`), `PreContratoPanel` (`:917`), renomear grupo (`~:1177`),
`ContratosPanel` (`FinanceiroSection.tsx:24`, `:72-100`), `LogisticaSection` (`:56`, `:381`, `:232`, `:250`),
`ObservacoesSection` (`:205-221`), `CastingSection` (`:634`, `RoleCard :318-440`, `PaymentStatusSelect :382`,
`AddRoleForm :684/:695`; WhatsApp já existe `:420`), `FigurinoSection` (`:107`, "Imprimir fichas" `:163-170`),
`EnsaioSection` (`:340`, `:374`, presença `:148`; `vincular.error` não é lido), `Presente3DSection` (`:106`, `:126`),
`FeedbackSection` (excluir avaliação `:84-85`).

**Caixa do cancelado** (`EventHeader.tsx:409-430`): hoje diz "Saiu da agenda e das listas de venda e de
cobrança; fica na página de Cancelamentos e, marcado, na ficha da cliente. Os dados abaixo ficam para consulta."
(`:426-429`; a T094 da 306 tirou de propósito a menção ao card). Escreve "Sem motivo registrado." com motivo
nulo (`:414-417`) — com a Q9 isso mentiria para quem não pode ver o motivo.

## Página de Cancelamentos, card e pendência do Casting

- **Página**: `GET /api/events/cancelamentos` (`agenda_write.py:870-881`), gate `_can_delete()` (`:114-118`, só
  Superadmin pelo papel real — de propósito, spec 306 Session 2026-10-15 item 1). Núcleo
  `listar_cancelamentos(*, flags)` (`cancel_ops.py:3397-3468`) com `resumo` em lote
  (`serializar_resumo_cancelado` `:516-583`: `pago`, `devolvido`, `devolucoes[]` com `estado`
  nao_pago/no_banco/pago e `pix` só com `show_financeiro`, `retido`, `principal`, `venda_passou_para`, `corte`; com
  `show_financeiro` também `imposto`, `taxa`, `comissao`, `bvs[].conta`). O `devolucao` legado (`_devolucao`,
  `:3420-3434`) segue "por um ciclo" — o ciclo já passou. Sem `mes`, sem filtro de estado, `limit(200)`
  (`:3411-3416`). Tela `EventosCancelamentosPage.tsx` (resumo, devoluções, `no_banco`; erro `:58-62` ainda diz
  "restrita ao Superadmin"); hook `useCancelamentos()` sem parâmetros (`lib/eventOps.ts:546-554`); menu só
  Superadmin (`lib/navigation.tsx:493-503`, `:502`); rota `App.tsx:100`.
- **Card da DRE**: `paineis.cancelamentos` (`financeiro_read.py:538-563`, de `totais_cancelamentos`) já traz
  `quantidade, pago, devolvido, devolucao_a_pagar, retido, comissao_retido, bv_retido, imposto,
  efeito_resultado` (nomes diferentes dos do plano: `devolucao_a_pagar` × `falta_devolver`, `bv_retido` ×
  `bv`). `itens[]` só tem `event_id, titulo, cancelado_em, retido, status`. `dre.{realizado,total}.retido_cancelamentos`
  e `n_cancelados` saem sempre (`financeiro/routes.py:273-274`). Nenhuma tela desenha o card; o tipo
  `CancelamentosDoPeriodo` existe (`lib/financeiro.ts:71-82`, `:115`) sem consumidor.
- **Dashboard Comercial**: só `kpis.retido_cancelamentos`, `n_cancelados`, `comissao_retido`, e só com cancelado
  (`vendas_ops.py:311-327`), no escopo do vendedor (`financeiro_read.py:160-164`). O bloco `cancelamentos` não
  existe. Cuidado: `totais_cancelamentos` soma `comissao_retido` sem filtro; o KPI filtra pelo beneficiário
  (`vendas_ops.py:314-321`) — o card tem de seguir a regra do KPI. Sublinhas já existentes:
  `VendasPipelinePage.tsx:104-128`; "↳ Retido de cancelamentos" em `FinanceiroDashboardPage.tsx:35-49`. Lugares:
  card da loja `VendasPipelinePage.tsx:325`; "📋 Eventos no Período" `FinanceiroDashboardPage.tsx:730`.
- **Pendência do Casting (Q10)**: a 306 já emite o sino `evento.cancelado_escala` (`notificacoes_ops.py:60`,
  `:76`, `:303-321`; `cancel_ops._avisar_no_sino` `:2237-2263`) ao papel CASTING, **um por dia**, `urgent` a 7
  dias, link `?aba=producao`, `entidade=("calendar_event", dia.id)`, chave `evento.cancelado_escala:<url_id>:<dia_id>`,
  título "tire N artistas da escala e avise cada um pelo WhatsApp", **corpo sem os nomes**. E-mail do ato
  (`cancel_ops.py:2282-2317`), elenco do ato (`event_cancellation_elenco`), multa tardia por `elenco_id`
  (`lancar_multas_do_cancelado` `:2396`, `POST /multas` `:757`). Falta tudo da 1c: `casting.cancelados_a_avisar`
  em `compute_casting_tasks` (`dashboard_service.py:53`; molde `serialize_unconfirmed_ref` `:277-295`; vizinho
  "Dispensar" da 308, `:150`), o bloco na Home (`DashboardPage.tsx`, molde `UnconfirmedRow` `:153`; tipo irmão de
  `UnconfirmedInviteRef`, `lib/types.ts:37`).
- **Portal e público**: nada mudou desde `f6ad283`. Ficha de figurino (`portal_figurino.py:36-37`;
  `PortalFigurinoPage.tsx:39-43` diz "Você não está escalado" para qualquer erro); avaliação pública
  (`feedback_write.py:45, :64`; `AvaliarPage.tsx`).

## Premissas do plano que caíram ou mudaram

1. **"Um vocabulário só, sem booleano `cancelado`, sem `payment_status: cancelado`" (premissa 2)**: a 306 criou
   `event_cancelled` (`gastos_read.py:54`), `cancelado` em `group.satellites[]` (`agenda_read.py:721`), nos eventos
   da ficha da cliente (`clientes_read.py:87-88`), na nota fiscal (`financeiro_read.py:475`) e no impacto
   (`cancel_ops.py:2531`), e o `payment_status` "cancelado" (`vendas_ops.py:46-58`, usado só nos itens do painel).
   `SeloSituacao.tsx:24-30` continua sem o ramo `cancelado`.
2. **Ficha da cliente**: a 306 manteve o cancelado na lista (P-43), o plano da 1c tira.
3. **Caixa do cancelado**: a 306 escreveu "marcado, na ficha da cliente" e sem o card — a 1c reescreve.
4. **Gate da página**: a 306 deixou só Superadmin; o Financeiro fica para a 1c (fechado a favor da 1c).
5. **Sino da Q10**: chave por dia e corpo sem nomes (o plano pedia nomes no corpo) — é da 1b/306 e funciona;
   `marcar_lidas_por_entidade("calendar_event", dia.id, KIND_EVENTO_CANCELADO_ESCALA)` serve por dia.
6. **E-mail de remoção no cancelado**: já calado pela 306 (Q12 = A), a 1c só confere.
7. **Ensaio no ato (Q3 = C)**: a 306 apaga os ensaios do banco e do Google (`cancel_ops.py:2205-2234`,
   `:2077`, `:2093`), avisa a equipe de Ensaio (`:2246-2251`) e recusa cancelar ENSAIO sozinho com 409 `ensaio`
   (`:1543-1548`). A 1c só recusa marcar/vincular ensaio a cancelado.
8. **Despachante Jinja**: a 306 recusa as ações de venda até ao Superadmin; a 1c pode recusar todas no
   cancelado pelo Jinja (a tela React é a porta das correções de venda).
9. **"Rota nova que escreve num evento existente entra na trava por padrão; fica livre só se a 1b a gatear por
   `pode_editar_venda_do_cancelado`"**: travaria o `PATCH …/motivo-cancelamento` da 306b (ordem do dono de
   20/10, posterior à Q7/Q8). A regra passa a ser: fica livre o que a 306 ou a 306b gateiam por regra própria.
10. **Q9 × 306b**: a spec da 306b deixou "esconder o motivo de algum papel" fora de escopo e escreveu que
    "Financeiro e os demais veem o motivo". A Q9 (13/10, "Apenas para os comercial, financeiro e admin mesmo")
    é resposta explícita e não revogada; a 306b só não tratou do assunto. Esconder do Casting, Figurino e Ensaio
    é compatível com a edição pela Comercial. O `docs/03` registra que a frase da 306b ficou superada.

## Dívidas do `docs/05` que encostam

- **#68** — `portal_figurino.py` dá 403 "Você não está escalado" em vez de 404; a dívida diz "trocar junto de
  alguma feature que já mexa na tela da ficha" — a 1c mexe (decisão no plan: a ordem da 302 fica, e a troca para
  404 não entra sem pedido).
- **#74** — ensaio e 3D no cancelado: quitada pela 1c.
- **#84** — o `docs/01` §3.3 não inventaria `/events/cancelamentos`.
- Nenhuma das 113–131 (da 306) cita a 1c.

## Verify da 306 para reusar (`specs/306-dinheiro-do-cancelamento/verify_306.py`)

`ROTAS` (`:118`), `preparar()` (`:1120`; usuários sa, com, fin, cast, fig, ens, mkt, a3d, vend, vend2, semcom;
talentos t, t2, t_sem_pix), `_usuario` `:557`, `_talento` `:577`, `_evento` `:613`, `_evento_com_elenco` `:658`,
`_escalar` `:681`, `_exemplo_padrao` `:1058`, `_cancelar_ok` `:1018`, `_corpo_cancelar` `:977`, `_dre` `:1052`,
`_detalhe` `:924`, `_resumo_api` `:930`, `_mes_corrente` `:3536`, `_vendedor_proprio` `:2117`, `_devolucao_avulsa`
`:794`, `_avisos_do_ato` `:6307`, `_ativos_do_papel` `:6320`, espião de remoção `:362-386`, `_remocoes_por_talento`
`:6331`, `_send_falso` `:353`, `_esperar_threads` `:415`, `_mutando`/`_sob_mutacao` `:6886-6918`, `limpar()` `:1289`,
`regressao()` `:7734`, `semear_tela()` `:7842`. Cenários-semente: 6, 20, 22, 24, 25, 28, 44, 45c, 48, 50.
