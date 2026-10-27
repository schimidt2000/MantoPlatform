# Reconferência do plano 2a (pedido de cancelamento) contra a `main` de 22/10 (`7cc5e11e`)

Três leitores só de leitura, em paralelo (backend; telas, portal e Jinja; RBAC, sino, verify e dependências),
conferindo o plano `docs/backlog/2a-solicitar-cancelamento-pelo-sistema.md` (escrito em 01–02/10 contra `f6ad283`,
respostas do dono de 13/10) contra o HEAD. Desde o plano entraram 305, 306 (o cancelamento com dinheiro — a "1b"),
306b, 309, 312 (o cancelado fora das listas — a "1c") e 313. **Vale esta reconferência onde ela diverge do plano.**
Linhas conferidas com `git show HEAD:`.

## 0. O que muda o desenho (resumo)

1. **A 1b e a 1c estão em produção.** O "aprovar" do pedido é o diálogo de cancelar da 306 (`ExcluirEventoDialog`,
   reescrito por ela — não há diálogo novo a substituí-lo). A D35 caiu: a 306 cancela também o evento marcado (303).
2. **O fecho do pedido tem gancho, mas o pedido é zerado antes dele.** `ao_cancelar(event, *, alcance,
   novo_principal)` (`cancel_ops.py:1594-1602`) é chamado em cada dia que o cancelamento encerra
   (`_encerrar_os_dias`, `:2063-2066`), mas as três colunas `deletion_*` viram nulo em `:2059-2061`, antes dele: o
   fecho da 2a precisa ler o pedido (autor, alcance) antes da limpeza.
3. **Vocabulário do alcance.** A 306 usa `alcance: "todos" | "so_este_dia"` (`constants.py:481-482`); o `venda|dia`
   do plano colide com `REGIME_VENDA/REGIME_DIA` (`:471-473`). E "so_este_dia" não cabe em `String(10)`.
4. **Migration.** Head `c5d2f7a9e306` (306); nada depois. As duas colunas propostas (alcance e devolução combinada)
   continuam necessárias — a 306 não guarda pedido.
5. **Q6 = C tem molde pronto.** A 312 (Q9) corta motivo e autor do **cancelamento** por `show_comercial`
   (`agenda_read.py:850-853`; `ver_motivo` na página, `cancel_ops.py:3605`). O **pedido** ainda vaza: o bloco
   `deletion_request` do detalhe (`agenda_read.py:854-862`) e os `pendentes[]` da página (`cancel_ops.py:3617-3629`)
   mandam motivo e autor a todo papel (inclusive o Superadmin em "Ver como Casting" e o revendedor EducaManto).
6. **A forma da devolução segue a da 306**: `devolucao {modo, valor, nome, pix, observacao}`, `venda_nova` no nível
   de cima; no corte de um dia só Parte ou Nada; nome e PIX obrigatórios onde há devolução; venda virtual ignora o
   modo. O pedido não revalida dinheiro (máximo, mínimo) — só a forma; quem valida o dinheiro é o cancelar.
7. **Nome no código.** `PedidoDeCancelamento` (`cancel_ops.py:981-1009`) já é o **corpo** do POST de cancelar: o
   pedido da 2a precisa de outro nome no código (ex.: "solicitação").
8. **Há um pedido real pendente em produção** — o evento 1350 (abaixo) —, e o "não há pedido antigo" do §10 do plano
   ficou falso.

## Recontagem em produção — 22/10/2026 ~05:20, transação READ ONLY por SSH

- **Pedidos da 224 pendentes: 1** — evento **1350** (R&I, 12/12/2026 19:00, com venda, 0 comprovante, sem cachê pago,
  sem grupo), pedido por um usuário COMERCIAL em **07/10 07:38**, motivo de 34 caracteres; às **07:44** o evento foi
  marcado como sumido do Google (303) — a equipe pediu no sistema **e** apagou no Google. **Ninguém decidiu em 15
  dias**: o pedido não avisa ninguém; o sino tem 6 avisos `evento.sumiu_google`, **0 lidos**. Recusas registradas: 0.
- Cancelados: 2, ambos em outubro (`event_cancellations`: 1 linha, regime venda, devolução Tudo).
- `audit_logs` desde 01/08: auto_deleted 2 (ago) · 3 (set) · 1 (out); manual_deleted 1 (ago); event_cancelled 2
  (out); sumiu_do_google 1 (out).
- Futuros vivos fora ENSAIO: **88**; com venda 76; com comprovante 53; com dinheiro 76; **com cachê pago 0**.
- Vendas de vários dias no futuro: **0** dias satélite, 0 principais com satélite.
- Usuários ativos com acesso: COMERCIAL 3 · SUPERADMIN 3 · CASTING 2 · REVENDEDOR_EDUCAMANTO 2 · FINANCEIRO 0.
- Sino por kind (total / lidos): form_response.nova 348/234 · avaliacao.recebida 66/7 · evento.sumiu_google 6/0 ·
  convite.recusado 5/1 · recado_nfc.novo 3/1 · evento.cancelado_escala 2/1.

## A. Backend
Três achados mudam o desenho: (a) `cancelar_evento` zera o pedido ANTES do gancho `ao_cancelar`; (b) o alcance do
plano (`venda|dia`) colide com `REGIME_VENDA/REGIME_DIA` e não é o vocabulário da 306 (`todos|so_este_dia`, 11
caracteres — não cabe em String(10)); (c) o head da migration é `c5d2f7a9e306` (306).

### 1. "Solicitar exclusão" (224) hoje
- Modelo: três colunas em `calendar_events` (`models.py:304-306`; comentário `:302-303`; por que não reusar para a
  marca `:308-313`); `has_pending_deletion_request` `:414-416`; `situacao` `:430-442` (cancelado > sumiu >
  exclusao_solicitada); `situacao_desde` `:445-451`. Não existe tabela de pedido.
- Rotas: `POST /api/events/<id>/solicitar-exclusao` `agenda_write.py:908-928`; `DELETE` (recusar) `:932-948`.
  Gates `_can_request_delete` `:185-189` → `_CAN_REQUEST_DELETE` `routes.py:69` (SA e COMERCIAL, papel real);
  `_can_delete` `agenda_write.py:120-124` → `_CAN_DELETE` `routes.py:68`.
- Núcleo: `solicitar_exclusao` `cancel_ops.py:3502-3521`, `recusar_solicitacao` `:3524-3541` — não avisam, não gravam
  AuditLog, não conferem pedido pendente/grupo/ensaio/marca/cachê; EventLog em horário de SP (`:3512`, `:3532`).
- 312: o POST chama `trava_do_cancelado` (`agenda_write.py:913-916` → `api_utils.py:23-33` →
  `cancel_ops.exigir_evento_vivo` `:3113-3117`): ordem viva 404 → 403 → 409 `cancelado` → 400 motivo. O DELETE
  segue sem trava. No cancelado `flags_do_detalhe` zera `can_request_delete` (`agenda_read.py:232-241`).
  `exigir_evento_vivo` diz que o pedido e a marca "não travam nada (FR-010)" (`cancel_ops.py:3114-3115`).
- `GET /events/cancelamentos` (`agenda_write.py:952-988`) usa `_can_read_cancelamentos` (SA ou FINANCEIRO, papel
  real, `:114-117`); `pendentes[]` (`cancel_ops.py:3617-3629`) manda `reason` e `requested_by` sem corte; os
  `cancelados` já usam `ver_motivo = show_comercial` (`:3612`, `:3634-3640`).
- Vazamento: `deletion_request` do detalhe sem corte (`agenda_read.py:854-862`); molde da 312 logo acima (`:852-853`).

### 2. O cancelamento da 306
- `cancelar_evento(event, *, corpo, actor) -> dict` `cancel_ops.py:2102-2175` (commita; Google e e-mails depois).
- `POST /api/events/<id>/cancelar` `agenda_write.py:721-763`, gate `_can_delete`; resposta `{ok, resumo, aviso,
  google_removido, gasto_id, dias_cancelados, venda_passou_para, ensaios_cancelados, avisados}`.
- Corpo (`PedidoDeCancelamento.ler` `:1008-1082`): `motivo`; `devolucao: {modo: tudo|parte|nada, valor, nome, pix,
  observacao}`; `alcance: "todos"|"so_este_dia"` (`constants.py:481-482`), só no principal com outro dia vivo (no
  satélite, mandar alcance = 400, `:1237-1241`); `novo_principal_id` (passagem; divergente = 409 `grupo_mudou`,
  `:1265-1266`); `venda_nova` e `venda_esperada` no nível de cima; `imposto_retido`; `bvs[]`; `multas[]`.
- Formas `FormaDoAto` avulso/todos/corte/passagem (`:1182-1199`, `:1228-1273`); a passagem pula compromisso interno
  ao escolher o novo 1º dia (`:1220-1225`).
- Regime venda (`_erros_do_pedido` `:1636-1680`): modo obrigatório; nada pago → só Nada; Parte valor > 0 e ≤ máximo;
  Tudo exige valor = `max_devolucao` senão 409 `max_devolucao_mudou` (`:1955-1962`); nome e PIX obrigatórios em Tudo
  e Parte, 200/120 (`:1683-1691`).
- Corte/passagem (`_erros_do_corte` `:1348-1377`): só Parte ou Nada; `venda_nova` obrigatória (`fields.venda_nova`);
  devolução mínima; nome e PIX só em Parte.
- Venda virtual: valida só motivo e imposto; modo ignorado (`:1653-1656`).
- Prévia `GET /impacto-exclusao?devolucao=&venda_nova=` (`agenda_write.py:655-664`); sem parâmetros `resumo_impacto`
  (`cancel_ops.py:2621`: `grupo.dias[].cache_pago`, `proximo_principal`, `acao`, `ensaios`, `elenco`). Só SA.
- Multa no ato (`multas[]`) e depois por `POST /events/<id>/multas` (`agenda_write.py:835-868`).
- Correções: `PATCH /devolucao` (`:766-798`), `PATCH /motivo-cancelamento` (306b, `:801-832`).
- Não existe desfazer do cancelamento (`EXCLUIR_CANCELADO` `agenda_write.py:147-148`, `routes.py:4572`).
- Gancho da 2a EXISTE: `ao_cancelar(event, *, alcance, novo_principal=None)` `cancel_ops.py:1594-1602` ("Ponto de
  extensão da 2a… sem efeito"), chamado em cada dia em `_encerrar_os_dias` (`:2063-2066`): "todos" com ALCANCE_TODOS;
  corte com SO_ESTE_DIA; passagem com o novo principal.
- BLOQUEANTE: as três colunas `deletion_*` viram nulo em `:2059-2061`, ANTES do `ao_cancelar` (`:2064/:2066`) — o
  gancho não sabe mais quem pediu. A 2a leva a limpeza para dentro do fecho (ou lê o autor antes).
- D27: o diálogo abre vazio (`ExcluirEventoDialog.tsx:177-186` não lê `deletion_request`); "pedido ao lado" e a
  tradução do alcance são trabalho da 2a.

### 3. Quem pode ser cancelado e os 409
- Ordem: trava do grupo (`:2128`) → `_recusas_de_estado` (`:1605-1617`) → forma → T6 → cachê pago → devolução
  pendente → 400 → 409 max.
- Já cancelado: 409 `ja_cancelado` (`:1609-1610`; UNIQUE → `ja_cancelado`, `:954`).
- Ensaio: 409 `ensaio` "Ensaio não se cancela sozinho: ele sai junto com o cancelamento do evento." (`:1612-1617`); no
  ato os ensaios são APAGADOS do banco (`_apagar_os_ensaios` `:2300-2315`).
- Cachê pago: 409 `cache_pago` com a lista de dias (`:2253-2264`), `FRASE_CACHE_PAGO` (`:2224-2227`), régua
  `_papeis_com_cache_pago` (`:2203-2221`, pago ou no banco, sem vaga de presença); `cache_pago_do_evento(event)`
  (`:2230-2238`, "exportada à 2a") olha UM evento; para todos os dias use `_papeis_com_cache_pago(ids)` ou
  `_dias_com_cache_pago` (`:2586`).
- Grupo: 400 `alcance`; 409 `sem_outro_dia_vivo`; 409 `grupo_mudou`.
- Novos: 409 `devolucao_pendente` (`:1620-1633`), `max_devolucao_mudou`, `tente_de_novo`; tabela
  `constants.py:624-641`, união `:642-649`. `pedido_pendente` e `sem_pedido` não existem.
- Marcado (303): o cancelar ACEITA o marcado e o desmarca no ato (`:2148-2150`); `EventoMarcadoError` (`:92-106`) só
  na exclusão. A frase da D35 citada no §2 do plano não existe mais.
- Excluir: 409 `cancelado` (`agenda_write.py:694-695`), "use o cancelamento" (`:696-701`), `sumiu_do_google`
  (`:712-713`), desagrupe (`:715-717`); `_delete_event_flow` (`routes.py:4540-4580`).

### 4. O sino
- Sete kinds (`notificacoes_ops.py:54-60`), destinatários `:64-77`; receita do kind novo na docstring `:16-18`;
  `emitir` (`:117-203`) ValueError fora do catálogo (`:153-154`); com `destinatarios` explícito o filtro de
  ativo/acesso é pulado (`:158-160`); dedupe (user_id, dedupe_key); título 200, corpo 500, chave 120.
- Urgente em ≤ 7 dias: `:272`, `:311`. Chave do ato da 306 `_chave_do_sino` (`cancel_ops.py:2279-2282`).
- `marcar_lidas_por_entidade` `:458-474`; `marcar_lidas_por_entidades` `:477-493`; `apagar_por_entidade` `:496-503`;
  molde "o aviso some sozinho" `fechar_pedido_ao_casting_se_vazio` (`cancel_ops.py:3101-3110`).
- `evento.pedido_cancelamento` / `pedido_decidido` NÃO existem.

### 5. Migration
- Head `c5d2f7a9e306` (306); nenhuma migration depois; `down_revision` da 2a = `c5d2f7a9e306`.
- Sem redundância: a 306 não criou coluna em `calendar_events`; `event_cancellations.refund_mode` e
  `sale_value_before/after` são do ato. As duas colunas propostas continuam necessárias.
- Alcance com `ALCANCE_TODOS/ALCANCE_SO_ESTE_DIA` — String(10) não cabe.
- Sem `db.JSON` no models (padrão Text); chaves alinhadas à 306 (`venda_nova` em cima, `observacao`); limites 200/120
  (`models.py:1110-1111`).

### 6. Linhas (plano → HEAD) — ver o relatório; principais: cancel_ops `cancelar_evento` 2102-2175, limpeza 2059-2061,
  `listar` 3564-3645, `pode_excluir` 3436-3453; agenda_write pedir 908-928, recusar 932-948, cancelamentos 952-988,
  impacto 637-666, delete 669-718, cancelar 721-763; routes `_delete_event_flow` 4540-4580, `_delete_event` 310-356,
  Jinja delete 4686-4715; notificacoes `emitir` 117, sumiço 355-389; sumico_ops `faixa_sumidos` 542-580; agenda.py
  154-157 / 160-172; agenda_read `deletion_request` 854-862, `situacao` 865, `_group_block` 706-753; constants 616-618.
- Desconhecidos: `api_utils.py:23-33` (`trava_do_cancelado`, `json_recusa_do_cancelado`); `flags_do_detalhe`;
  `serializar_cancelamento`; `EventCancellation*`; `event_ops._apagar_ensaio_no_banco` (`:1849-1861`);
  `orcamento_evento_ops.travar_evento`; `cobranca_ops.compromisso_interno`; `group_ops.py:33-41` (passagem: o antigo
  1º dia vira satélite).

### 7. Premissas
- P2/D35/§2: a 306 já aceita cancelar o marcado. Sistema do §2 não existe mais.
- "Três linhas no cancelar_evento": contradita pela ordem limpeza → gancho. Grupo já travado (`travar_grupo` `:846`);
  pedir e recusar seguem sem trava.
- Erro do pedido: 409 `cancelado` já sai pela trava da 312; o cancelar usa `ja_cancelado`.
- P5/P16: o Financeiro já lê `/events/cancelamentos`, com motivo e autor dos pendentes sem corte.
- P13: EventLog do cancelamento já UTC (`:2096-2097`); pedir/recusar em SP.
- P17: o próximo dia pula compromisso interno; na passagem o antigo 1º dia vira satélite.
- P22/P23: venda virtual ignora o modo; no corte o campo é `venda_nova`; nome e PIX só em Parte no corte (Tudo
  recusado).
- P26: `cache_pago_do_evento` cobre um dia só; recusa nova `devolucao_pendente`.
- P27: `_apagar_ensaio_no_banco` já apaga avisos; gêmeo Jinja (`routes.py:2825-2826`) e o cascade de `_delete_event`
  (`:333-335`) não; no cancelamento os ensaios são apagados.
- Confirmadas: P28, P29 (`notificar_evento_cancelado`/`notificar_cancelamento_na_escala` `:285-322`,
  `_mandar_os_emails` `:2385`), P31, P32/D27, P18 (`apagar_por_entidade` `routes.py:354`), P10
  (`exclusao_solicitada` `constants.py:618`).
- Importação cíclica: `sumico_ops.py:37` importa `cancel_ops.total_recebido` no topo → `cancel_ops` importa
  `sumico_ops` dentro da função.
- Não conferido: se `GET /api/events/<id>` do cancelado continua aberto a todo login (P30).

## B. Telas, portal e Jinja
### 1. Plano × hoje
- Menu "Solicitar exclusão": `EventHeader.tsx:363-373` (dentro de `if (!cancelado)` `:355`, 312); `MOTIVO_SO_DEVOLVER` `:41-42`; no cancelado `can_request_delete` desligado (`agenda_read.py:241`).
- Banner do pedido `EventHeader.tsx:462-495`: motivo e autor a todo papel; "Sem motivo informado." (`:466`); "Recusar solicitação" sem confirmação (`:482-491`); "Analisar e decidir" (`:474-481`) já abre o diálogo de cancelar da 306; banner do sumiço antes (`:456-460`); caixa do cancelado (312, `:414-453`) já tem o corte da Q9 (`:422-429`).
- O diálogo da 1b NÃO substitui o `ExcluirEventoDialog`: a 306 o reescreveu (729 l.), serve a excluir (`acao==="excluir"`, `:427-436`) e cancelar; montado em `EventHeader.tsx:522-527`.
- `SolicitarExclusaoDialog.tsx`: Input de uma linha `:71-76`, corpo `{motivo}` `:43-45`.
- `EventosCancelamentosPage.tsx`: título `:158`; "Aguardando decisão" `:174-228`; "Abrir evento" `:217-219`; desde a 312 abre a Superadmin E Financeiro pelo papel real (`agenda_write.py:114-117`, `:961`); Comercial 403.
- `navigation.tsx`: DUAS entradas "Exclusões e cancelamentos" — `:388-396` (Financeiro) e `:504-513` (Superadmin).
- `eventOps.ts`: hooks `:441-471`; moldes `setQueryData` `:19`, `:45`; `CodigoDevolverAoGoogle` `:474-482`; `CancelamentoPendente` `:516-524`; `CodigoRecusaCancelamento` `:95-117` (conferida pelo verify contra a lista do servidor).
- `agenda.ts`: `deletion_request` `:435-439`; tipo de situação já inclui `exclusao_solicitada` (`:11`).
- `NotificacaoItem.tsx`: mapa `:7-16` (306 acrescentou `evento.cancelado`, `evento.cancelado_escala`); `Bell` `:36`.
- `SeloSituacao.tsx`: `:32` só comentário ("é da 2a"); ramo novo em `:37-55`; devolve null hoje para `exclusao_solicitada`.
- Tooltips Mês/Dia: `CalendarGrid.tsx:78-82`, `DayTimelineView.tsx:124-127` só `sumiu_do_google`; `AgendaListView.tsx:59` herda pelo `SeloSituacao`.
- `SumiuDoGoogleBanner.tsx`: frase do Comercial `:45-49`; botões Superadmin `:65-76` (306 pôs "Cancelar o evento", `:71-75`); `QuadroEmJogo` `:114-160` (não reusar).
- `useFaixaSumidosVisivel`: `EventDetailPage.tsx:193`, `DashboardPage.tsx:1046`.
- `agenda_read.py`: `deletion_request` `:854-862`; `group` `:706-752` (satélites `:731-744` com `cancelado`; principal vivo tira o dia cancelado `:743`); `show_comercial` `:172`; resumo `:70-95`; `flags_do_detalhe` `:207-244` (`somente_consulta`).
- `models.py`: `deletion_request*` `:302-306`; `has_pending_deletion_request` `:414-416` (exclui cancelado); `situacao`/`situacao_desde` `:429-451` JÁ devolvem `exclusao_solicitada` (precedência cancelado > sumiu > pedido).
- Portal: `portal_ops.py:321` (`em_confirmacao = bool(event.is_google_missing)`, em `_role_summary` `:268-332`); `PortalAgendaPage.tsx:40`, `PortalConvitesPage.tsx:42`, `PortalHistoricoPage.tsx:51`, `portalAgenda.ts:59`; texto em `AvisoEmConfirmacao.tsx:15-26`.
- Jinja: botão `event_detail.html:116-121` E o modal repete o `if` em `:2381-2398`; rota já recusa o Comercial (`_CAN_DELETE` → 403, `routes.py:4691-4692`).

### 2. Faixa vermelha
- `FaixaSumidosGoogle.tsx:28-163`, montado para todo usuário em `AppShell.tsx:169`; dado `useSumidosGoogle` (`sumidosGoogle.ts:37-47`) → `GET /api/events/sumidos-google` (`agenda.py:160-172`); quem vê `_ve_faixa_sumidos` (`agenda.py:154-157`, Superadmin ou Comercial pelo papel efetivo; senão `pode_ver:false`); conteúdo `faixa_sumidos()` (`sumico_ops.py:542-580`, "sem dinheiro, motivo nem autor").
- No componente: `total/visivel/unico/frase` `:36-41`; barra de altura fixa `h-10` `:77`, `:82-118`; lista irmã `:123-160` com UM `aberto` (`:31`), UM `botaoRef` (`:33`), UM `listaId` (`:34`) — duas frases pedem o estado em dobro; `visivel = total > 0` (`:38`) e o `select` de `sumidosGoogle.ts:60` viram `total > 0 || pedidos.total > 0`; tipo `FaixaSumidos` `:15-22`.
- `invalidarSumidosGoogle` (`sumidosGoogle.ts:66-68`) já chamado por `useCancelarEvento` (`eventOps.ts:367`), `useDeleteEvent` (`:87`), `useSyncEvent` (`:62`), `useDevolverAoGoogle` (`:502`, `:510`); faltam os hooks de pedir e recusar (`:450-453`, `:466-469`).
- Contrato: `total` continua contando SÓ sumidos (bundle velho escreveria "N eventos sumiram").

### 3. Diálogo de cancelar da 306 e o D27
- Props só `eventId, eventTitle, open, onOpenChange` (`ExcluirEventoDialog.tsx:155-160`); dados `useImpactoExclusao` (`eventOps.ts:284-291` → `agenda_write.py:637-665`, `_can_delete`) e `usePreviaCancelamento` (`:294-300`); o impacto não traz o pedido (`cancel_ops.resumo_impacto` `:2621`).
- Abre vazio no modo e no alcance (`DEVOLUCAO_VAZIA` `:55`, alcance null `:184`, multas vazias; zera ao fechar `:207-223`), mas pré-preenche o nome com `cliente_nome` (`:197-203`) e o novo valor com `venda_do_grupo` (`:204-206`).
- Para o pedido ao lado: prop opcional nova (de `data.event.deletion_request`, `EventHeader.tsx:522`), bloco só leitura depois de `ResumoImpacto` (`:517`); coluna `max-w-xl`, rolagem `max-h-[65vh]` (`:494`, `:514`) → "ao lado" vira "acima".
- Vocabulário: 306 usa alcance `"todos" | "so_este_dia"` (`eventOps.ts:219`; `ALCANCE_TODOS/SO_ESTE_DIA`, `cancel_ops.py:2052`).
- O cancelamento já zera `deletion_*` em cada dia (`cancel_ops.py:2058-2061`).
- Blocos reusáveis `CancelamentoDevolucaoBloco` (props `:19-39`), `CancelamentoDiasBloco` (`:21-34`) pedem `pago`, `maxDevolucao`, `GrupoDoImpacto` (do impacto, só Superadmin).

### 4. Portal
- Somar `or event.has_pending_deletion_request` em `portal_ops.py:321` cobre convites, próximos, passados e Histórico (`:357-386`, `:397-400`, `:936`; Histórico `start_at < now` `:924`).
- Satélite com pedido de todos os dias: `_com_evento` só `selectinload(EventRole.event)` (`:170-180`); ler `event.group_leader` = N+1 (comentário `:318-320` promete "nenhuma consulta nova"). (Hoje há 0 vendas de vários dias futuras em produção.)
- Portal Jinja não mostra o aviso; sem gêmeo.

### 5. Selo na agenda
- `SeloSituacao.tsx:37-74`; servidor já manda o código (`serialize_event_summary`, `agenda_read.py:81`, `:93-94`).
- A 312 criou a CHAVE `event_situacao` em `clientes_read.py:109`, `formularios_admin_read.py:74`, `figurino/producao_ops.py:554`, mais `situacao` em `nfc_ops.py:374` → o ramo novo acende o selo também em `ClientDetailPage.tsx:244`, `FigurinoProducaoDetailPage.tsx:621`, `FigurinoProducaoListPage.tsx:498/:504`, `FormulariosAdminPage.tsx:265/:498`, `Tags3DPage.tsx:276`.

### 6. Q6 = C
- Corte da 312 para o cancelamento: `agenda_read.py:850-853` (`show_comercial`); página `ver_motivo` (`cancel_ops.py:3605`, `:3633-3640`); tela `EventHeader.tsx:422-429`.
- O pedido ainda não tem corte: `agenda_read.py:857-858` (autor e motivo a todo papel); `cancel_ops.py:3618-3622` (pendentes) ignora `ver_motivo` — Superadmin em "Ver como Casting" lê.

### 7. Desconhecidos e linhas erradas
- `main.tsx:16-27` (`aoRecusarMutacao`, `queryClient.ts:37-40`): `codigo:"cancelado"` já recarrega; `pedido_pendente`/`sem_pedido` são de cada hook.
- `lib/recusaDoCancelado.ts`, `EditarMotivoDialog.tsx`, `CardCancelamentosDoPeriodo.tsx`, blocos da 306 (`CancelamentoDevolucaoBloco`, `CancelamentoDiasBloco`, `CancelamentoBvBloco`, `MultaAoElencoBloco`, `ResultadoCancelamento`).
- Backend de passagem: `agenda.py` 148-151 → `:154-157`, 154-166 → `:160-172`; `sumico_ops` 533-571 → `:542-580`; `agenda_write` 625-662 → `:908-949`, 665-674 → `:952-986`; `api_delete_event` `:671`; `routes.py` 4214-4248 → `:4540-4587`; Jinja `:116` e `:2381`.
- Texto: "Exclusão solicitada" (`EventHeader.tsx:464`).

### 8. Deploy cruzado
- Bundle velho × backend novo: `POST/DELETE /solicitar-exclusao` só com `{motivo}` (`eventOps.ts:446`, `:462`) → o alias TEM de aceitar o corpo velho (Q2 = B exige devolução); banner velho escreve "Sem motivo informado." quando `reason` nulo (enganoso, não quebra); selo velho null e faixa velha ignora `pedidos`; o pedido só aparece no poll de 60 s.
- Bundle novo × backend velho: `pedidos`/`pedido_bloqueado` opcionais; `POST /pedido-cancelamento` 404 → o hook mostra o erro e não grava cache.
- Portal: `em_confirmacao` já existe; o backend sozinho liga o aviso.
- Jinja: trocar o `if` do botão e o do modal juntos.

## C. RBAC, sino, verify, dependências e dívidas
### 1. RBAC
- Fontes: `docs/00` §4 (`:87-166`), `docs/01` §4.3 (`:1906-2072`; tabelas "RBAC do evento cancelado" 306 `:1956`, "O
  cancelado fora das listas" 312 `:2022`).
- Pedir: `_CAN_REQUEST_DELETE={SUPERADMIN,COMERCIAL}` (`routes.py:69`), papel real (`agenda_write.py:185-189`); flag
  `can_request_delete` pelo papel efetivo (`agenda_read.py:196`), zerada no cancelado (`:241`). POST: 404 → 403 →
  `trava_do_cancelado` (409 `cancelado`) → 400 `fields.motivo` (312).
- Recusar/cancelar/excluir: `_can_delete` só SA papel real (`routes.py:68`, `agenda_write.py:120`); DELETE de recusar
  (`:932-948`) sem trava nem lock.
- Ninguém desfaz cancelamento. 306b: editar motivo do cancelado (SA ou Comercial, papel real; `docs/01:1921`), deixou
  de fora o motivo do pedido (`specs/306b-motivo-editavel/spec.md:68`).
- Fila: `_can_read_cancelamentos` (SA ou Financeiro, papel real; `agenda_write.py:114-117`, 312); Comercial 403.
- Faixa: `_ve_faixa_sumidos` (`agenda.py:154-157`), SA ou Comercial pelo papel efetivo; endpoint `:160-172`.
- Motivo: `show_comercial` `agenda_read.py:172`, `show_financeiro` `:181`; cancelamento cortado (`:852-853`); o bloco
  `deletion_request` (`:854-861`) sem corte, e o banner desenha (`EventHeader.tsx:462-470`); `pendentes[].reason`
  (`cancel_ops.py:3622`) ignora `ver_motivo` (`:3605`) — no "Ver como Casting" o motivo aparece.
- Revendedor alcança `/api/events` (`app/__init__.py:55`) e lê hoje o motivo do pedido (2 ativos). Casting 2 ativos;
  no cancelado só ele e o SA tiram da escala; recebe `evento.cancelado_escala`. Financeiro 0. Elenco no portal sem
  papel; `em_confirmacao` só da marca (`portal_ops.py:321`); cancelado sai do portal (`:223`, `:355`, `:924`).
- Sino: `DESTINATARIOS_POR_KIND` (`notificacoes_ops.py:64-77`) sem kind de pedido; `emitir(destinatarios=...)`
  (`:117-160`) serve ao `pedido_decidido` endereçado ao autor; `ANTECEDENCIA_URGENTE_DIAS=7` (`:91`).
- Nenhum gate do plano mudou de nome nem de regra; gates novos a respeitar: `trava_do_cancelado`/`exigir_evento_vivo`
  (312), `_can_read_cancelamentos` (312), `pode_editar_*_do_cancelado` (306/306b).

### 2. Falta × já feito
- Falta (a 2a): kinds `evento.pedido_cancelamento` e `pedido_decidido`; rota `/pedido-cancelamento` + alias com 409
  `pedido_pendente` (hoje `solicitar_exclusao` sobrescreve um pedido aberto sem avisar); recusas de ensaio e cachê pago
  na porta do pedido; `AuditLog cancel_requested`; as duas colunas; Q6 = C no detalhe e na fila; Q4 = C (selo — o
  comentário do `SeloSituacao.tsx` diz "é da 2a" —, `em_confirmacao` do pedido, satélite lendo o pedido do principal:
  `situacao` lê só a própria coluna, `models.py:433-445`); Q1 = B (chave `pedidos` na faixa, `agenda.py:170-172`,
  `lib/sumidosGoogle.ts:15-16`); o bloco "o que foi pedido" ao lado do diálogo vazio (D27; a 306 deixou para a 2a:
  `specs/306-dinheiro-do-cancelamento/spec.md:461`, `:1321-1322`, `:2446`); a troca de nome (`EventHeader.tsx:363-371`,
  `SolicitarExclusaoDialog.tsx:60`).
- Já feito: `ao_cancelar` no-op (`cancel_ops.py:1594-1603`), chamado em toda forma (`:2062-2066`), com espião no
  `verify_306.py:384-412`; limpeza das três colunas (`:2058-2061`); régua do cachê pago e recusas
  (`_papeis_com_cache_pago` `:2203`, `cache_pago_do_evento` `:2230`, `FRASE_CACHE_PAGO` `:2224`; códigos `ensaio`/
  `cache_pago` `constants.py:624-646`); passagem do 1º dia e devolução Tudo/Parte/Nada com nome e PIX (`:1683-1692`);
  invalidações do front no cancelar/excluir (`lib/eventOps.ts:87`, `:366-368`); 312: "o pedido não esconde nem trava
  nada" (`specs/312-cancelado-fora-das-listas/spec.md:349`, `docs/04:219`).
- D18/D21/D24 em produção para o sumiço (303); a 2a estende ao pedido. D35 caiu com a 306 (o marcado se cancela,
  `docs/01:1969`): o 1350 (marcado e com pedido) já pode ser aprovado hoje pelo "Analisar e decidir".

### 3. Tamanho e premissas
- ~89 → ~82–84 tarefas (M). Sai: laço/ponto da 1b, `onSuccess`, recusa no cancelado e 400 com fields, importação da
  régua/frase do cachê pago, cenário 37 (coberto pelo `verify_312` c14), §4.3 da página. Entra: classificar a rota nova
  no 9b do `verify_312` (`:695-715`), o pedido legado 1350 (migration aceitando nulos; sino retroativo?), o corte Q6 em
  `pendentes`, alinhar nomes à 306.
- P17: usar `ALCANCE_TODOS="todos"`/`ALCANCE_SO_ESTE_DIA="so_este_dia"` (`constants.py:480-482`); 0 grupos futuros.
- P27: código `ensaio` existe; o ato apaga os ensaios (`cancel_ops.py:2068`). P28 pronta. P30: o link `/events/<id>`
  vale; exclusão sem link (P18). P31 construída e verificada na 312 (vira regressão).

### 4. Verify
- Padrão vigente: a 312 importa o harness da 306 como módulo (`verify_312.py:7-13`, `:44-46`): `GoogleFalso` que falha
  fechado + disjuntor de rede (`verify_306.py:17-21`, `:254`), e-mail falso, espião de remoção, usuários `_usuario`
  com prefixo (`:557-575`); conexão separada `_externo` (`:158`); eventos em meses isolados (2047–2049); sai com
  código 2 se o backend local estiver rodando; mutação `_sob_mutacao` (`:6895`); `*_primeira_falha.txt`;
  `--regressao` com base JSON.
- Cenários do plano: 10 e 31–36 perdem a condição "só com a 1b"; 13 já é a trava (`agenda_write.py:917-920`; coberto em
  `verify_312.py:1472-1474`) → regressão; 19: `scripts/db/verify_cancelamento_evento.py` envelhecido (26/44, dívidas 85
  e 129) sai da regressão; entram `verify_303.py:2375-2377` e `:2583`, `verify_312.py:225-229` (semeia o pedido por
  SQL) e `LIVRE_306` `:706-707`; 31 usava evento real com cachê pago → refazer descartável; 34 trivial (ensaio apagado)
  → só "o kind do pedido não vai ao Casting"; 37 redundante; 22 exige trava (`travar_grupo` `:846`,
  `traduzir_erro_de_banco` `:954`); 18a por `_sob_mutacao`; 5 pela diferença antes/depois.
- "Deve falhar" (9, 15–18b, 23) exigidos (constituição VIII, `:165`).

### 5. Dívidas
- 76 (P3, `docs/05:498`): EventLog de solicitar/recusar em SP (`cancel_ops.py:3510`, `:3529`) → a 2a quita a parte da
  224. 85 e 129 (P4): verify da 224 envelhecido → só tirar da regressão. 91 (P3): BV não prende o evento na exclusão
  → citar no cenário 11. 78 (P4): sexta cópia do fechar em Esc → opcional.
- Não registradas: motivo do pedido sem corte (detalhe e fila "Ver como" — o tipo do incidente de 20/10 que levou à
  306b) e a sobrescrita silenciosa de pedido aberto → a 2a quita.

### 6. Números (recontagem minha, produção 22/10)
- 1 pedido pendente (1350, R&I 12/12, com venda, COMERCIAL, 07/10 07:38; marcado sumiu_do_google 07:44; 0 comprovante;
  sem cachê pago; sem grupo; motivo de 34 caracteres); sino `evento.sumiu_google` 6 / 0 lidos; 88 futuros vivos fora
  ENSAIO, 76 com dinheiro (venda), 53 com comprovante, 0 com cachê pago; 0 grupos futuros; 2 cancelados (1 em
  `event_cancellations`, venda/tudo); usuários ativos: COMERCIAL 3, SUPERADMIN 3, CASTING 2, REVENDEDOR 2, FINANCEIRO
  0; audit desde 01/08: auto_deleted 2+3+1, manual_deleted 1, event_cancelled 2, sumiu_do_google 1.
- O "Scripts: nenhum; não há pedido antigo" do §10 ficou falso: decidir o sino retroativo do 1350.

### 7. Contradições
- 312 Q9 × 2a-Q6 = C batem (mesmo trio). O diálogo de cancelar ainda diz "Aparece para quem abre o evento."
  (`ExcluirEventoDialog.tsx:589`), texto da 306b superado pela Q9 → corrigir.
- Colisão de vocabulário: `PedidoDeCancelamento` (`cancel_ops.py:981-1009`) é o corpo do POST de cancelar;
  `_encerrar_os_dias` grava `cancellation_reason = pedido.motivo` (`:2057`) → o pedido da 2a precisa de outro nome no
  código (ex.: "solicitação").
- Q2 = B × 306: regras batem; formato diverge (`venda_nova` em cima, `fields.venda_nova`); o corte tem devolução mínima
  (`:1371-1374`) → o pedido não revalida dinheiro, só a forma.
- Q5 = D × 306b: não se contradizem.
- D35 contradiz a 306 (substituída): cenário "o SA cancela o marcado com pedido".
