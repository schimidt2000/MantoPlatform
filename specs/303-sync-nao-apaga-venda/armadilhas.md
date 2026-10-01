# Armadilhas do código de hoje — 303

Levantadas em 30/09 pelos agentes que rascunharam as tarefas, com `arquivo:linha` conferido no
código daquele dia (`main` em `14cec75`). São notas de trabalho para quem implementa: leia as do
trecho antes de começar a fase. As linhas andam — localize pelo conteúdo.

## Setup e Foundational (inclui o verify)

- app/calendar/routes.py:19-29 — o módulo importa por nome cinco funções do service que falam com o
  Google; trocar `service.insert_event` não alcança `routes.insert_event`. O dublê tem de entrar em
  `service.build` (import em service.py:10) e `service.load_credentials` (service.py:93), que toda
  função resolve na hora da chamada.
- app/calendar/routes.py:2197-2208 — `sync_events` pula item com `created` de menos de 5 minutos e
  sem linha local: os itens do dublê nascem SEM `created`, senão a semeadura e o cenário 8 passam a
  vazio.
- app/calendar/sync.py:51-70 e :83-85 — o ciclo vai do mês corrente até o último evento do banco + 1
  mês; com eventos de teste em 2031+, são ~70 listas por ciclo, e todo mês não liberado levanta 503
  no dublê. Consequência: `errors > 0` e `sync_erro` em TODO ciclo do verify — 'conta como falha' só
  se afirma pela linha do mês em `results[]` do `cleanup_past`, nunca pelo status do ciclo.
- app/api/admin_config_write.py:92-108 — o 'Limpar eventos fantasma' varre todo mês que tem evento
  no banco, passados e futuros; um dublê que devolvesse lista vazia para mês real apagaria (hoje) ou
  marcaria (depois) os eventos reais do espelho. O falha-fechado não é opcional.
- app/calendar/routes.py:153-163 — `_mark_month_synced` guarda só 24 meses e descarta os mais
  antigos: sincronizar meses de teste expulsa meses reais de `site_settings.calendar_sync_cache`; o
  verify guarda e restaura.
- app/email_service.py:25-63 e :980 — o e-mail de mudança de data e o alerta de ensaio saem por
  thread (`send_async`; chamadas em app/calendar/event_ops.py:75 e :81): afirmar 'zero e-mail' sem
  `_esperar_threads()` passa por corrida. A captura tem de ser em `_send`, que é quem confere
  `MAIL_SUPPRESS_SEND` — capturar depois dele não veria nada.
- app/calendar/routes.py:2060-2078 e :2272-2277 — todo SHOW importado ganha a vaga 'Técnico de Som'
  com o talento REAL 42 e dispara alerta à equipe de ensaio; cenário de data passada não usa SHOW, e
  a vaga sai com o evento na limpeza.
- app/calendar/routes.py:1923-1932 e :2361-2392 — o título vira personagem e a reconciliação apaga
  vaga fora do título, com e-mail de remoção ANTES: o marcador de teste vai na descrição, e a vaga
  'fora do título' do 10g nasce pelo endpoint real (`agenda_write.py:163`) em evento descartável.
- app/calendar/routes.py:2410-2434 — `_mark_talents_worked` roda a cada `sync_events` e liga
  `worked_before` em talentos reais do espelho pela regra de produção; a limpeza do verify não
  desfaz (mesmo efeito de qualquer sync).
- app/calendar/sync.py:140 e app/__init__.py:240-243 — `calendar_auto_sync_at` é UTC (`utcnow`), não
  `now_sp()`: a guarda de 15 minutos compara com UTC. Em desenvolvimento a thread só sobe com
  `WERKZEUG_RUN_MAIN=true`.
- app/models.py:238-241 — o índice parcial `ix_calendar_events_cancelled_at` (migration
  b8e4d27a91f5:48-51) NÃO está declarado em `__table_args__`: drift antigo, não consertar junto; o
  índice novo é declarado nos dois lugares.
- app/calendar/service.py:93-132 — `load_credentials` abre um `app_context` aninhado; o ramo que
  renova o token (:128-130) nunca dispara — `save_token` não grava `expiry` e `creds.expired` é
  sempre falso; a renovação acontece no 401, dentro do `.execute()` (`google_auth_httplib2`), e o
  `RefreshError` do token revogado sai de lá. Em `consultar_evento`, `RefreshError` em qualquer ponto
  → `sem_credencial`.
  `fetch_single_event` (:181-191) segue intocada e o import dela em `routes.py:24` só sai na fase 3.
- app/config.py:188 e :384-385 — a chave nova vai na classe-base `Config` (o nome é reatribuído para
  Production/Development no fim do arquivo); carregar o `config.py` em processo filho com
  `FLASK_ENV=production` grava `instance/.secret_key` (:163-185).
- app/notificacoes/notificacoes_ops.py:101 — o cenário 13b injeta a falha embrulhando o atributo
  `emitir` do módulo (existe hoje); só funciona se o produtor novo morar nesse módulo e chamar
  `emitir` pelo nome global, como os outros produtores (:195-290).
- Dublê — `reset()` não pode esquecer `itens` e `apagados`: id desconhecido responde 503 (falha
  fechado), e um evento marcado esquecido de outro cenário abriria o disjuntor da reconferência
  (R12) e tornaria inconclusivos os marcados do cenário seguinte.
- Dublê — 'credencial por chamada' contada do início do ciclo quebra depois da fase 4:
  `reconferir_marcados` chama `load_credentials` antes do laço de meses. O índice conta a partir da
  lista do mês-alvo (zerar quando o `list` daquele mês responde), senão as variantes de credencial
  do 13 passam a vazio.
- specs/205-loja-interacoes-virtuais/verify_205.py:1581 e :1585 — a restauração de `insert_event`
  está no corpo do `try`, não no `finally` do script; e `gcal_service` só é importado em :550 —
  restaurar no `finally` global daria `NameError` se o script falhar antes. Usar `try/finally` local
  em volta do V7.2. O nome `consultar_original` (:569) já é da operadora.
- app/calendar/routes.py:4318-4341 — a rota antiga de exclusão é Jinja com `@login_required`: a
  sessão aberta por `POST /api/auth/login` vale para ela; a resposta é um 302 (não seguir o
  redirecionamento) e a prova é o banco por conexão separada.

## História 1

- app/calendar/routes.py:163, :2352, :2358, :2406, :2434 — `_mark_month_synced`, `sync_events` e
  `_mark_talents_worked` comitam sozinhos: não existe transação do mês; a unidade de trabalho da
  limpeza é o evento, e todo commit expira os objetos carregados.
- app/calendar/routes.py:352-368 + app/models.py:352-357 — o laço de hoje percorre instâncias
  carregadas antes; com commit por evento, o ensaio-filho apagado por cascade junto com o pai vazio
  chega à sua vez fora da sessão. Materializar ids e reler com `db.session.get` (`None` = já saiu,
  não é falha).
- app/calendar/cancel_ops.py:57-74 — `pode_excluir` conta qualquer vaga com talento, então devolve
  'não vazio' para todo SHOW (a vaga automática do técnico): não serve para a regra do sync.
  `total_recebido` (:47-54) serve e deve ser reusado.
- app/calendar/cancel_ops.py:139-155 — `aplicar_estorno_comissao` (chamado por `_delete_event`,
  routes.py:325-327) só trata `a_pagar` e `pago`; comissão `pago` vira estorno negativo contra o
  vendedor e `no_banco` não é tratada. A comissão paga NÃO segura o evento (decisão do dono, 30/09):
  o evento vazio com comissão `pago` é apagado e o estorno sai, como hoje. A comissão `no_banco`
  presa ao evento é comportamento de hoje, fora do escopo.
- app/calendar/orcamento_evento_ops.py:227-245 — o orçamento cria a vaga extra `Técnico de Som` em
  evento de QUALQUER tipo, sem talento; `_ensure_sound_technician` (routes.py:2067-2078) só roda em
  SHOW. A exceção do técnico automático exige `event_type == SHOW`, senão o talento 42 escalado pela
  equipe fora de SHOW seria descartado.
- app/notificacoes/notificacoes_ops.py:39-41 — o módulo importa só db/models/constants; `sumico_ops`
  vai importá-lo, então `PresoAoEvento` só pode entrar sob `TYPE_CHECKING` (ciclo de import).
  `emitir` recusa kind fora do catálogo (:137-138) e só engole `IntegrityError` no savepoint
  (:163-183): qualquer outra exceção do produtor sobe — é o que o cenário 13b exercita.
- app/api/agenda_read.py:210-214 — o histórico do evento converte `EventLog.created_at` de UTC para
  São Paulo. O `EventLog` da marca NÃO recebe `created_at` (o cancelamento passa horário de São
  Paulo em cancel_ops.py:206-212 e sai 3 h adiantado — dívida, não copiar).
- R6 lista `EventLog` antes do produtor do sino, mas o texto do `EventLog` leva 'Aviso enviado a N
  pessoa(s)': o produtor tem de rodar antes, e com o carimbo local do `UPDATE` (o objeto ORM fica
  com a marca velha até o `refresh`).
- app/calendar/sync.py:83-85 e app/api/admin_config_write.py:107-108 — os dois `except` do mês não
  fazem rollback hoje; o novo é SÓ para `SQLAlchemyError`. Os e-mails de `sync_events` saem antes do
  commit (routes.py:2277, :2341, :2391): rollback em erro que não é de banco repetiria o e-mail a
  cada ciclo. `admin_config_write.py` não importa `db` hoje; o `except` de `sync_now` (:80-81) fica
  como está.
- app/calendar/sync.py:79 e app/api/admin_config_write.py:104-106 — são os dois únicos consumidores
  do retorno de `_cleanup_stale_events` (os dois com `len()`); entre a delegação (T042) e os ajustes
  (T043, T045) o ciclo e o admin ficam quebrados. O wrapper Jinja `/agenda?force_sync=1`
  (routes.py:470-482) ignora o retorno e só captura `RuntimeError`: nenhuma linha muda ali — o
  `elif` citado no plano é o do wrapper do Sincronizar (routes.py:4244-4249).
- app/calendar/routes.py:19-29 — o service é importado por NOME no topo; depois da FR-039
  `fetch_single_event` (:24) fica sem uso em routes.py (ruff F401). O verify antigo
  `scripts/db/verify_151_excluir_sync.py` troca `routes.fetch_single_event` e passaria a consultar o
  Google real; `scripts/db/verify_168_admin_config_react.py` devolve lista onde o admin passa a ler
  `ResultadoLimpeza`. Nenhum dos dois roda sem ajuste.
- app/calendar/event_ops.py:638 e :649-659 — a condição do marcado vai no `if` do push, não depois:
  com `google_ok` falso, troca de tipo que envolve SHOW é desfeita e levanta
  `EventTypeChangeBlocked` (409). Sair de SHOW num evento marcado apaga os ensaios do Google de
  verdade (risco registrado em research §Riscos).
- app/calendar/routes.py:4203-4206 — hoje o botão Sincronizar entrega a `sync_events` o item
  apagado: com a resposta mínima, o título vira 'Sem título' (:2229), as datas ficam nulas e a
  escala é reconciliada com e-mail de remoção (:2390-2392). O ramo ausente não pode chamar
  `sync_events` em hipótese nenhuma.
- app/calendar/routes.py:320 e app/models.py:575 — `_clear_event_side_tables` só limpa as tabelas do
  pai; `EventLog.event_id` é NOT NULL sem cascade. `apagar_por_entidade`
  (notificacoes_ops.py:400-407) filtra só por entidade, sem kind — hoje nenhum outro kind usa
  `calendar_event`.
- app/api/agenda.py:85-90 — a visão Dia não filtra cancelado; quem garante que a marca nunca aparece
  em evento cancelado é a precedência de `CalendarEvent.situacao` no servidor. A tela lê `situacao`,
  nunca recombina `cancelled_at`, marca e pedido de exclusão.
- frontend/packages/ui/src/components/badge.tsx:6-10 — `Badge` só aceita `tone`, `className` e
  `children`: o tooltip do selo (`title`) precisa de um `span` em volta. O tipo `SituacaoEvento`
  (lib/agenda.ts) e o componente têm nomes diferentes de propósito: o arquivo é `SeloSituacao.tsx`,
  que exporta `SeloSituacao`; o tipo entra por `import type`.
- frontend/apps/internal/src/components/AgendaListView.tsx:57-60 — o `span` do título contém o
  subtítulo da cliente (usado pela busca); o selo vai fora dele.
  frontend/apps/internal/src/components/CalendarGrid.tsx:117 — o chip é `truncate` com
  `hover:opacity-80` e ~80 px: só o ícone cabe.
- frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:236 — 'Sincronizar' só aparece
  com `google_html_link`; como o servidor passa a mandar o link nulo no evento marcado, sem a
  condição nova o botão some e o 409 fica inalcançável pela tela. A mensagem do 409 já aparece em
  :411.
- frontend/apps/internal/src/components/notificacoes/NotificacaoItem.tsx:49-58 — título e corpo são
  `truncate` dentro de uma linha `flex items-center`; o `line-clamp` vale para TODO aviso `urgent`
  (avaliação com nota baixa e recusa em cima da hora também mudam de altura no painel e em
  /notificacoes).
- frontend/apps/internal/src/pages/AdminSyncPage.tsx:15, :23, :34-38 — os dois botões compartilham
  `runSync.isPending` e a mesma caixa de resultado; `sync_now` devolve `count`, não os números
  novos. Linhas por mês e tom de alerta têm de tratar campo ausente como zero.
- Datas no front: 'percebido em dd/mm/aaaa' sai por `formatShortDate` de `@manto/ui` (fonte única,
  que lê ISO sem fuso como horário local — `packages/ui/src/lib/date.ts`; não copiar o
  `formatDataCurta` de `EventHeader.tsx:33-37`, que é cópia local), nunca por `toISOString()` —
  `google_missing_since` é horário de parede de São Paulo, sem fuso. `formatShortDate(null)` devolve
  "—": onde o texto pede `sem data`, tratar o nulo antes.

## Histórias 5 e 2

- app/calendar/routes.py:2352, :2358, :2406 e :2434 — `sync_events` comita sozinho e chama
  `_mark_talents_worked`, que comita de novo. Consequências: `desmarcar` + `sync_events([item])`
  saem num commit só (o do sync); depois dele o objeto ORM expira (ler o id antes); e não há como
  segurar uma transação em volta de `sync_events`.
- app/calendar/routes.py:2229-2236 — o que `sync_events` grava: título =
  `_strip_reserved_title_segments(summary or "Sem título")`; descrição e local crus (podem ser
  None); datas por `parse_event_datetime` (service.py:194-214: dia inteiro vira meia-noite naive,
  com o fim exclusivo). `mesmos_dados` tem de reproduzir exatamente isso, senão um evento fora da
  lista dá "mudou" a cada 10 minutos.
- app/calendar/sync.py:78-79, app/api/admin_config_write.py:103-104 e app/calendar/routes.py:474-475
  — os três chamadores rodam `sync_events(items)` ANTES da limpeza. Quando `limpar_mes` encontra um
  marcado de volta na lista, o Google já foi aplicado (inclusive o e-mail de mudança ao elenco
  aceito, routes.py:2340-2342, e a reconciliação da escala com e-mail de remoção, :2361-2392):
  `limpar_mes` só desmarca.
- app/calendar/routes.py:364-365 — o filtro de candidatos de hoje é por `start_at` dentro do mês. O
  filtro do "marcado cujo id voltou" NÃO pode reusá-lo: tem de ser por id em `live_ids`, sem faixa
  de mês.
- app/calendar/service.py:148-156 — a lista do mês usa `singleEvents=True` e `showDeleted=False`: id
  na lista = presença certa (dispensa consulta), e série recorrente-mãe nunca vem na lista (cai
  sempre no ramo `presente` sem mudança — é para ela o `presente_fora_da_lista` com
  `serie_recorrente`).
- app/calendar/routes.py:4191 — `_sync_single_event_flow(event)` não recebe ator; só tem dois
  chamadores (routes.py:4243 e app/api/agenda_write.py:631). Na tela, o item "Sincronizar" só
  aparece para quem tem `show_casting` (EventHeader.tsx:236), mas a API não tem gate: o ator pode
  ser qualquer usuário interno.
- app/models.py:577 e :594 — `EventLog.actor_role` e `AuditLog.actor_role` são String(60); o par de
  papéis juntado por vírgula (agenda_write.py:532) passa disso para quem tem vários papéis, e o
  Postgres recusa: cortar em 60. `EventLog.created_at` tem default `utcnow` (models.py:579) e a tela
  converte (agenda_read.py:210-214): não passar `created_at` — o log "Evento criado" do próprio sync
  passa horário de São Paulo (routes.py:2268) e não é molde.
- app/models.py:600 — `AuditLog.created_at` é UTC (`utcnow`); `notifications.created_at` e a marca
  são São Paulo. A deduplicação "uma vez por evento e dia" do `presente_fora_da_lista` compara com
  uma coluna UTC; `_log_sync` grava `entity_type="agenda"` (routes.py:409) e o índice
  `ix_audit_logs_entity` (models.py:588) cobre a consulta.
- app/calendar/sync.py:79 e :83-85 — hoje o ciclo faz `len(_cleanup_stale_events(...))` e o `except`
  do mês não tem `rollback`; os dois são toques da História 1. Se ainda estiverem assim quando a
  fase 4 começar, a fase 3 não terminou. O detalhe do ciclo corta a lista de meses nos oito
  primeiros (:100): os números da reconferência têm de ir nos totais, antes dela.
- Fronteira entre as fases 3 e 4: a História 1 tem de deixar o desfecho `presente` de
  `_decidir_candidato` como no-op (não apaga, não marca) e o ramo `presente` do "Sincronizar"
  chamando `sync_events` como hoje, sem desmarcar. Se a fase 3 tratar `presente` de outro jeito, as
  tarefas T067 e T071 mudam de ponto de toque.
- app/__init__.py:55 e :747-751 — o guard do revendedor devolve 403 para todo `/api/*` fora de
  `/api/auth`, `/api/agenda`, `/api/events` e `/api/educamanto`; `/api/events/sumidos-google` passa
  pelo prefixo. Rotas fixas sob `/events/` hoje: `new/options` (app/api/agenda.py:142),
  `new/prefill` (:155) e `cancelamentos` (app/api/agenda_write.py:609); todas as dinâmicas usam
  `<int:…>` — sem colisão. `_role_flags` ignora `impersonate_role` de quem não é Superadmin real
  (agenda_read.py:154-155).
- frontend/packages/ui/src/lib/date.ts:46-50 — `formatShortDate(null)` devolve "—", e a faixa pede
  `sem data`. `start_at` chega como ISO naive de São Paulo: nunca passar por `toISOString`.
- frontend/apps/internal/src/lib/useAuth.ts:58-66 e :83, :95 — o logout só zera `ME_KEY` (por isso o
  id do usuário na chave da faixa) e o "Ver como" invalida todas as queries (a faixa reavalia
  `pode_ver` sem código extra). O observer passivo precisa da MESMA chave, com o id, senão nunca
  enxerga o cache. O QueryClient padrão tem `staleTime` de 30 s e foco desligado
  (packages/api-client/src/queryClient.ts:39-40).
- Camadas: não existe nenhum `z-[N]` arbitrário no app hoje (busca vazia em frontend/**/src) — a
  faixa inaugura o degrau. Vizinhos: régua de abas `z-20` (EventDetailPage.tsx:242), barra do mobile
  `sticky top-0 z-30 h-14` (packages/ui/src/components/app-layout.tsx:194), painel do sino `z-30`
  (NotificacoesPanel.tsx:68), sidebar `z-40` (app-layout.tsx:189).
- Offsets de topo: os dois únicos consumidores no app interno, conferidos hoje por busca, são
  frontend/apps/internal/src/pages/EventDetailPage.tsx:242 e DashboardPage.tsx:1002; o `sticky
  top-0` de components/Modal.tsx:56 é interno ao diálogo e não muda. EventDetailPage não importa
  `cn` hoje (linha 4). Classe Tailwind montada por interpolação não é gerada: as duas variantes têm
  de aparecer inteiras no código.
- frontend/apps/internal/src/components/AppShell.tsx:158 — o sino é condicionado por
  `isRevendedorOnly(user)`; a faixa não pode copiar essa condição (o front não decide RBAC). O
  esqueleto do shell (:137-149) retorna antes do `AppLayout` e fica sem faixa.

## História 3 e FR-045

- app/api/agenda_write.py:522-527 — `api_delete_event` testa `pode_excluir` ANTES de chamar
  `_delete_event_flow`: todo marcado com venda, pagamento, contrato ou escalado recebe o 409
  genérico (sem `codigo`, mandando usar o cancelamento) e nunca chega à recusa do núcleo.
- app/api/agenda_write.py:564-565 — `except CancelValidationError` responde 400 com `fields.motivo`;
  `EventoMarcadoError` é subclasse e tem de ser capturada antes, senão o 409 `sumiu_do_google` vira
  400.
- app/api/agenda_write.py:104-107 — `_event_detail_json` já devolve `Response`; não dá para somar
  `devolucao_google` nele. O molde de chave extra é `api_create_event`, `:845-848`.
- app/calendar/routes.py:4224-4225 e :4332-4337 — `_delete_event_flow` devolve `(False, None)` para
  líder e o wrapper Jinja traduz esse `False` em "desagrupe os satélites". A recusa do marcado tem
  de ser exceção e vir antes; reaproveitar o `False` daria a mensagem errada.
- app/calendar/routes.py:4318-4341 — a rota antiga `POST /events/<id>/delete` não passa por
  `pode_excluir`: hoje ela apaga de vez um evento com dinheiro. Sem `try/except`, a exceção nova
  vira 500.
- app/calendar/routes.py:2350-2353 e :2361-2392 — o sync só pula a reconciliação quando `source ==
  "platform"`; fora disso apaga vaga não-extra que não está no título e manda e-mail de remoção
  (`:2390-2392`). Nome reservado é migrado para `extra`, não apagado (`:2382-2389`): não conta como
  "fora do título".
- app/calendar/routes.py:2190-2208 — a guarda da 254 só cobre item do Google com menos de 5 minutos
  e sem linha local: entre `insert_event` e o commit não pode entrar consulta pesada nem chamada
  externa.
- app/calendar/service.py:266-288 — `update_event` (usado por `_push_cabecalho_ao_google`,
  `event_ops.py:541-558`) sempre manda `dateTime` e só manda `location` quando não é vazio: no ramo
  "já tinha voltado", dia inteiro vira bloco com hora e local apagado no sistema não é apagado no
  Google.
- app/calendar/service.py:217-263 — `insert_event` de hoje não tem `all_day` (chega no
  Foundational). O fim de dia inteiro no banco já é o exclusivo do Google (`parse_event_datetime`,
  `:194-214`): não some um dia.
- app/calendar/cancel_ops.py:272 e :299-305 — o cancelamento grava `EventLog.created_at` em São
  Paulo sem fuso; `_serialize_logs` (`app/api/agenda_read.py:210-214`) trata sem-fuso como UTC e a
  linha sai 3 h errada. Não copie: o EventLog da devolução não passa `created_at`.
- app/calendar/cancel_ops.py:286 — o cancelamento devolve `{exc}` do Google ao usuário; não copie.
  As mensagens da devolução são as fixas do contrato; o tipo do erro vai só para o AuditLog.
- app/models.py:577 e :594 — `actor_role` é `String(60)` em EventLog e AuditLog. Corte em `[:60]` e
  dê `flush` ANTES do Google: estouro depois do insert deixaria evento órfão na Agenda.
- app/calendar/routes.py:393-414 — `_log_sync` monta `gcal:<google_event_id>` na hora da chamada:
  chame `google_returned` antes de trocar o id, senão a auditoria perde o id velho.
- Trava: `CALENDAR_SUPPRESS_EVENT_WRITES` tem de ser lida de `current_app.config` a cada chamada (o
  verify a desliga em `app.config` no mesmo processo). Guardar em constante de módulo quebra o 10a
  ou o 10.
- frontend/packages/ui/src/components/confirm-dialog.tsx:48 e :60 — o `ConfirmDialog` só desabilita
  o botão "Cancelar" durante `pending`; Esc, clique fora e o X (dialog.tsx:77) chamam
  `onOpenChange(false)` direto. O bloqueio de fechamento é do consumidor.
- frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:217-220 — `anunciar` apaga a
  mensagem em 2,2 s; a frase do `reapareceu` é longa.
- TanStack Query 5 — callback passado a `mutate()` não dispara se o componente desmontou. O banner
  some quando o `setQueryData` tira `sumiu_do_google`; por isso o hook e o estado do diálogo ficam
  no `EventHeader`.
- frontend/apps/internal/src/lib/eventOps.ts:11, :52 — os hooks vizinhos tipam o erro como `Error`.
  O `codigo` está em `ApiRequestError.details.codigo`
  (`frontend/packages/api-client/src/client.ts:18-37`); falha de rede não é `ApiRequestError`.
- frontend/apps/internal/src/components/EventDetail/parts.tsx:64-68 — `formatRange` mostra `00:00 —
  00:00` no dia inteiro e perde o dia do fim; `formatDay`/`formatTime` (`:31-40`) passam por `new
  Date()`. `start_at`/`end_at` são horário de parede de São Paulo: nada de `toISOString()`.
- app/api/agenda_read.py:762-765 e :1060-1063 — o detalhe de ENSAIO volta antes de `elenco`,
  `pagamentos` e `kpi`, e `kpi` só existe com `show_financeiro`. O quadro do banner tem de tolerar
  chave ausente.
- app/api/agenda_read.py:357-358 — no satélite, `kpi` vem do principal do grupo; mostrar
  `kpi.sale_value` ali diria a venda do grupo como se fosse do evento. Por isso o satélite troca as
  linhas de dinheiro pela frase com link.
- frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx:118-128 — o cartão da aba
  Comercial rotula `Comissão (N%)` e põe "estimativa" na dica. O quadro do banner usa o rótulo
  `Comissão (estimativa)` do R15; só a condição é a mesma, e `formatRange`/`KpiCard` não são
  reaproveitáveis aqui.
- frontend/packages/ui/src/components/accordion-row.tsx:45-57 — `summary` é renderizado dentro de um
  `<button>`: só texto, sem link nem botão.
- app/api/agenda_read.py:189 × app/api/agenda_write.py:83-87 — `flags.can_delete` segue o "Ver
  como"; `_can_delete()` olha o papel real. Superadmin vendo como Comercial não vê o botão, mas a
  API aceita — herança da 224, não corrigir aqui.
- EventHeader.tsx também é tocado na US1 (Sincronizar e "Editar no Google Agenda", hoje `:236-248`):
  as linhas citadas nas tarefas T097 e T104 terão andado. Localize pelo conteúdo.

## História 6 e Polimento

- Raiz do repo: C:\Users\schim\Desktop\Manto_Platform. Nenhum código da 303 existe:
  `google_missing_since`, `sumico_ops`, `consultar_evento`, `em_confirmacao` e `AvisoEmConfirmacao`
  não aparecem em `app/` nem em `frontend/apps/`.
- `_role_summary` (app/talent_portal/portal_ops.py:268-328) é a fonte única de quatro listas —
  `pending_invites`, `upcoming` e `history` (:401-403) e `items` do histórico (:921). A chave nova
  entra num ponto só, e não pode custar consulta por escalação (a docstring, :284-287, explica que
  tudo chega pronto de fora).
- As consultas do portal já filtram cancelado (portal_ops.py:351, :357, :370, :379 e :909):
  `em_confirmacao` nunca chega verdadeiro para evento cancelado — mas a propriedade tem de continuar
  sendo "marca E não cancelado", não só a coluna preenchida.
- `_event_ids_in_window` (app/talent_portal/portal_rating_ops.py:115-119) faz join com
  `CalendarEvent` e NÃO filtra cancelado; `_require_open_event` (:225-236) só confere escalação e
  término. É o defeito do 24b, vivo hoje.
- `_require_open_event` tem três chamadores (portal_rating_ops.py:267, :331, :411) e um adaptador só
  (app/api/portal_ratings.py:28-31, `json_error(exc.message, exc.status)`). A docstring do módulo
  (:3-4) ainda fala em "view Jinja legada", mas `app/talent_portal/routes.py` não tem rota de
  avaliação — não há segundo caminho a fechar.
- Efeito aceito do 400 em evento cancelado: quem já tinha avaliado perde a leitura da própria
  avaliação pelo portal (`serialize_rating_form`, portal_rating_ops.py:411, passa pela mesma
  função). A nota segue gravada.
- A caixa vermelha de alteração da Agenda traz o botão "Ciente"
  (frontend/apps/portal/src/pages/PortalAgendaPage.tsx:39-62), que zera `event_changed_at`
  (portal_ops.py:439-447). O aviso novo não pode reusar esse mecanismo: ele dura enquanto a marca
  durar.
- No Histórico o título usa `truncate` dentro de um `div` `min-w-0`
  (frontend/apps/portal/src/pages/PortalHistoricoPage.tsx:29-30). O aviso tem de ficar fora desse
  bloco, senão é cortado em 320 px.
- `bg-gold-soft` ainda não é usado no portal — só `text-gold-ink` (PortalAgendaPage.tsx:71). O token
  existe no preset (frontend/packages/ui/tailwind-preset.ts:77;
  frontend/packages/ui/src/theme.css:95-96 no claro e :192-193 no escuro): confira os dois temas.
  `text-gold` reprova contraste; texto é `text-gold-ink` (docs/04_GUIA_DE_DOMINIOS.md:504).
- Busca por `em_confirmacao` também casa `sem_confirmacao` (app/marketing/virtuais_ops.py:2298;
  app/calendar/invite_reminders.py:55; frontend/apps/internal/src/lib/virtuais.ts:453) — falso
  positivo em varredura por substring.
- app/calendar/sync.py:7-8 diz que o ciclo faz "a MESMA" operação do botão "Sincronizar agora" — mas
  `sync_now` (app/api/admin_config_write.py:64-90) não limpa; só `cleanup_past` (:92-117) e o ciclo
  limpam. O texto já é falso hoje.
- `app/calendar/routes.py` tem 8 erros antigos de `ruff check` (docs/05_DIVIDA_TECNICA.md:477, item
  55): o comando do quickstart §5 sobre `app\calendar` não volta limpo, com ou sem a 303.
- As citações `arquivo:linha` do docs/04 estão velhas: ele dá `_cleanup_stale_events` em
  `routes.py:245` (hoje :341), `_delete_event_flow` em `:3743` (hoje :4211), o sync de um evento em
  `:3723` (hoje `_sync_single_event_flow`, :4191) e `sync_events` em `:2149` (hoje :2184). Cite por
  nome de função (docs/05, item 62).
- docs/04_GUIA_DE_DOMINIOS.md:182-185 descreve um `flash()` dentro de `_delete_event` que não existe
  mais: a função devolve o aviso (app/calendar/routes.py:305-338). Quem reescrever o trecho da
  limpeza vai esbarrar nele.
- docs/01_SISTEMA_E_BANCO.md não lista os endpoints da 224 (`/cancelar`, `/solicitar-exclusao`,
  `/impacto-exclusao`, `/events/cancelamentos` — app/api/agenda_write.py:484-609), e a linha :1533
  dá `_can_delete()` como COMERCIAL e SUPERADMIN, quando `_CAN_DELETE = {SUPERADMIN}`
  (app/calendar/routes.py:64).
- O cabeçalho do docs/01 tem seis rótulos "head" de features antigas (:11, :20, :23, :35, :43, :84);
  o head real hoje é `e5a1c7d93b20` (nenhuma migration em `migrations/versions/` o tem como
  `down_revision`). O `docs/00_MAPA_DO_SISTEMA.md:9` ainda diz `b7d2e4f1a9c3`.
- docs/05: o maior número de item é 68 (:489) e o 61 está fora de ordem (:490) — dívida nova começa
  em 69. A dívida 49 está em :471 e a fatia A em :347.
- docs/03 é append-only e tem 5.351 linhas: índice em :118-120, "Índice por assunto" em :251-268,
  molde da entrada em :278-280, Registro em :285, entrada mais nova em :287. Não leia o arquivo
  inteiro.
- Os três `EventLog` de `cancel_ops` gravam `created_at` em São Paulo
  (app/calendar/cancel_ops.py:206-211 solicitar, :223-228 recusar, :299-304 cancelar) — a dívida do
  "3 h adiantado" cobre os três, não só o cancelamento.
- Depois de `scripts\db\refresh-local-db.ps1` a migration local some (quickstart §1): sem `flask db
  upgrade` e `python seed.py` de novo, verify e telas quebram por coluna inexistente.
- O verify exige o backend local PARADO (sai com código 2 se `calendar_auto_sync_at` for recente);
  as telas exigem o backend local LIGADO, com `MANTO_SEM_THREADS=1` e `FLASK_ENV=development`. No
  local, o "Limpar eventos fantasma" e o "Sincronizar" leem o Google real com o token do espelho
  (FR-024) — só a devolução é travada.
- Edição de documento só pelo Edit tool: `Get-Content -Raw` + `Set-Content` regrava os acentos como
  mojibake e ninguém acusa (CLAUDE.md §7). Varredura de prosa precisa juntar as linhas: o texto
  quebra em ~100 colunas e a frase atravessa a quebra.
