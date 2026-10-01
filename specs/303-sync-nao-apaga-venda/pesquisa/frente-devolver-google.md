# Frente devolver-google

Devolver ao Google Agenda e a trava de escrita (FR-012, FR-024) — endpoint, núcleo, trava do Princípio XIV, botão na tela e ensaios-filho

Tamanho: M — 1 endpoint novo, 1 função de núcleo (~120 linhas) no módulo da marca, 1 trava nova em app/config.py, 1 parâmetro opcional em insert_event, 1 hook + 1 ConfirmDialog + 2 botões no EventHeader, ~11 cenários de verify (10, 10a–10i, 11). Sem migration própria (usa a coluna da marca, que é da frente da marca). Depende de duas funções de outras frentes: a consulta de três estados ao Google e o desmarcar por reaparecimento (FR-006).

## DG-1 — (a) Qual é o endpoint de devolver ao Google — caminho, módulo, gate, resposta e erros?

**Decisão.** POST /api/events/<int:event_id>/devolver-ao-google em app/api/agenda_write.py, logo depois de api_cancelar_evento. Corpo vazio. Gate _can_delete() (só SUPERADMIN, papéis reais) no início da view, depois do 404. A view só chama sumico_ops.devolver_ao_google e serializa. Sucesso = 200 com o detalhe do evento (serialize_event_detail) mais a chave devolucao_google.resultado ('recriado' | 'reapareceu'). Erros no envelope json_error com a chave extra `codigo`: 404 evento inexistente; 403 sem permissão; 409 cancelado / nao_marcado / venda_virtual / sem_data / google_travado; 502 google_inconclusivo / google_recusou.

**Porquê.** agenda_write.py já hospeda as duas outras saídas da mesma decisão (cancelar, :541-566) e o gate pedido pela spec (_can_delete, :83-87); o módulo já está importado em app/api/__init__.py, então não há registro novo a esquecer. Devolver o detalhe do evento repete o padrão de /sync e /confirm (eventOps.ts:50-57 faz setQueryData) e evita um GET a mais. 502 para falha do Google é o que api_create_event já usa (:816-821) e o que /sync usa (:634-635). O `codigo` existe para o verify afirmar o ramo exato sem casar prosa; a tela mostra só error.message. /api/events/ passa pelo guard do revendedor (app/__init__.py:739-751).

**Alternativas rejeitadas.** (1) Módulo novo app/api/sumico_write.py — rejeitado: exigiria import em app/api/__init__.py e duplicaria os gates _can_delete/_event_detail_json que vivem em agenda_write. (2) Responder {ok: true} como o cancelar (:566) e invalidar a query — rejeitado: a tela ficaria um ciclo mostrando a marca até o refetch. (3) Flags booleanas no erro (padrão orcamento_de_outro=True, agenda_write.py:1248) — rejeitado: são 7 motivos mutuamente exclusivos; um discriminante só é mais simples no TypeScript e no verify. (4) 503 para a trava de ambiente — rejeitado: 5xx some nos monitores como queda; é recusa por estado, 409.

**Contrato.** POST /api/events/<int:event_id>/devolver-ao-google · corpo: nenhum · RBAC: _can_delete() (SUPERADMIN real; ignora 'Ver como').
200: { ...EventoDetalhe, "devolucao_google": {"resultado": "recriado" | "reapareceu"} }
Erros: {"error": {"message": <pt-BR>, "codigo": <str>}}
- 404 (sem codigo) 'Evento não encontrado'
- 403 (sem codigo) 'Sem permissão'
- 409 cancelado — 'Este evento está cancelado.'
- 409 nao_marcado — 'Este evento não está marcado como sumido do Google Agenda.'
- 409 venda_virtual — defensivo; venda virtual nunca é marcada
- 409 sem_data — 'Este evento está sem data ou horário. Edite a data antes de devolver ao Google Agenda.'
- 409 google_travado — 'Este ambiente não escreve no Google Agenda (trava de desenvolvimento). Nada foi criado e a marca continua.'
- 502 google_inconclusivo — 'Não foi possível consultar o Google Agenda agora. A marca continua — tente de novo em instantes.'
- 502 google_recusou — 'O Google Agenda não aceitou criar o evento. A marca continua — tente de novo em instantes.'
TypeScript (frontend/apps/internal/src/lib/agenda.ts, EventoDetalhe): devolucao_google?: { resultado: 'recriado' | 'reapareceu' } (opcional).

**Pontos de toque.**
- app/api/agenda_write.py:541-566 (inserir a view nova depois de api_cancelar_evento)
- app/api/agenda_write.py:83-87 (_can_delete — reuso, sem mudança)
- app/api/agenda_write.py:104-107 (_event_detail_json — reuso)
- app/api/agenda_write.py:6-10 (comentário RBAC do topo: citar a rota nova)
- app/api_utils.py:16-42 (json_error com **extra — reuso)
- app/__init__.py:739-751 (guard do revendedor libera /api/events — sem mudança)
- docs/01_SISTEMA_E_BANCO.md:691 (tabela §3.3) e §4.3 (linha do gate)

**Riscos.**
- O gate usa papéis reais: Superadmin 'vendo como COMERCIAL' não vê o botão (flag com impersonação, agenda_read.py:155,189) mas a API aceita — comportamento herdado da 224, não muda aqui.
- 502 também é o status que o proxy Node fabrica quando o Flask cai; a tela distingue pela mensagem do envelope, não pelo status.

**Verify.** Cenário 11 (DEVE falhar): usuário COMERCIAL REAL (não impersonação) faz POST → 403; por conexão separada: marca, google_event_id e contagem de EventLog inalterados; dublê de insert com 0 chamadas. Cenário 10i: POST em evento não marcado → 409 codigo=nao_marcado; em evento cancelado → 409 codigo=cancelado; id inexistente → 404. Todas as requisições fora de app.app_context(), login por POST /api/auth/login.

**Revisão adversarial: parcial.** Caminho, módulo, gate e status sustentam: os vizinhos fazem 404 e depois `_can_delete()`, e `json_error` aceita `**extra`, que chega à tela em `ApiRequestError.details`. O 502 do proxy Node sai como texto puro, então a tela de fato distingue pela mensagem. Três furos no contrato: (1) `_event_detail_json` devolve um `Response` já serializado, então não dá para somar `devolucao_google` nele; o molde certo é o de `api_create_event`, que chama `serialize_event_detail` e acrescenta a chave antes do `jsonify`. (2) No 409 `nao_marcado` ou `cancelado` o cache `['event', id]` está velho (outra aba, outro Superadmin, ou o ciclo desmarcou entre a consulta e o bloqueio). Como a tela só mostra `error.message`, o diálogo fica aberto com erro e a faixa da marca continua na tela de um evento que já está resolvido. (3) Token do Google revogado ou desconectado cai em `google_inconclusivo` com 'tente de novo em instantes', que não se resolve sozinho; o Jinja já separa esse caso e aponta para /google/connect.

**Emenda.** (1) Na view: `result = serialize_event_detail(event, current_user, session.get('impersonate_role'))`, `result['devolucao_google'] = {...}`, `jsonify(result)`; tirar `_event_detail_json` dos touchpoints. (2) No hook, `onError`: se `error.details.codigo` for `nao_marcado` ou `cancelado`, invalidar `['event', eventId]` e a chave da faixa e fechar o diálogo com um aviso neutro. Alternativa no servidor: tratar 'já não está marcado' como sucesso idempotente. O cenário 10f confere o comportamento escolhido. (3) Acrescentar o código `google_desconectado` (502), com a mensagem que aponta para /google/connect, para `RuntimeError('Google não conectado')` e falha de refresh. (4) Tipar `codigo` como união literal no TypeScript.

**Evidência da revisão.** app/api/agenda_write.py:104-107 (`_event_detail_json` devolve jsonify), :548-552 (404 antes do gate), :845-848 (molde de chave extra); app/api_utils.py:16-42; frontend/packages/api-client/src/client.ts:29-37, :115-125; frontend/server.js:664-673 (502 do proxy em text/plain); app/calendar/routes.py:4045-4047 (mensagem de Google desconectado)

## DG-2 — (b) Onde mora e o que faz a função de núcleo (ordem dos passos, transação, log, auditoria)?

**Decisão.** Função devolver_ao_google(event_id, *, actor) no módulo de núcleo da marca (app/calendar/sumico_ops.py — se a frente da marca escolher outro nome de arquivo, vai junto com marcar/desmarcar). Ordem fixa: (1) carrega e valida sem bloqueio (existe, não cancelado, marcado, não VIRTUAL, start_at e end_at preenchidos); (2) trava de ambiente (DG-7) — ambiente travado não faz NENHUMA chamada ao Google; (3) consulta o id velho (DG-4); (4) bloqueia a linha com SELECT … FOR UPDATE + populate_existing e revalida a marca; (5) insert_event (DG-3); (6) _log_sync ANTES da troca (para o detalhe gravar 'gcal:<id velho>'), troca google_event_id e google_html_link, source='platform' (DG-6), tira a marca pelo helper único de desmarcar da frente da marca (sem commit), EventLog com o ator, marcar_lidas_por_entidade do aviso do sino; (7) commit imediato. Não toca deletion_requested_*, grupo, venda, escala nem ensaios.

**Porquê.** A constituição (III) manda núcleo em *_ops.py sem flask.request; calendar já tem esse padrão em cancel_ops.py e event_ops.py, então não é preciso pôr nada novo em routes.py. O bloqueio FOR UPDATE com populate_existing é o mesmo remédio da 298 contra clique duplo (formularios_ops.py:172-186, agenda_write.py:767-774): sem ele, dois POSTs simultâneos criam dois eventos no Google e o primeiro vira órfão que o sync importa como evento vazio. A consulta vem antes do bloqueio para a linha ficar presa só durante o insert (~1 s, custo já aceito na 298). _log_sync antes da troca reaproveita o prefixo 'gcal:' (routes.py:402-403) e deixa o id velho na auditoria — única pista se ele voltar da lixeira. EventLog com agora = datetime.now(tz=TZ).replace(tzinfo=None), convenção do cancel_ops.py:272.

**Alternativas rejeitadas.** (1) Pôr a função em cancel_ops.py — rejeitado: o módulo é 'cancelamento e solicitação de exclusão'; devolver compartilha estado com marcar/desmarcar, não com o dinheiro. (2) Pôr em routes.py ao lado de _sync_single_event_flow — rejeitado: a regra é não engordar routes.py, e cancel_ops/event_ops provam que o domínio já aceita *_ops. (3) Sem bloqueio, com UPDATE condicional depois do insert (WHERE marca IS NOT NULL) e delete compensatório do evento recém-criado quando perder a corrida — rejeitado: troca um bloqueio de 1 s por uma segunda escrita externa que pode falhar e deixar órfão. (4) Bloquear antes da consulta — rejeitado: dobra o tempo de linha presa sem ganho.

**Contrato.** class DevolverAoGoogleError(Exception): codigo: str; message: str; status: int

def devolver_ao_google(event_id: int, *, actor: User) -> dict[str, Any]:
    """Commita. Returns {"event": CalendarEvent, "resultado": "recriado" | "reapareceu"}.
    Raises DevolverAoGoogleError (codigos de DG-1)."""

Efeitos no ramo 'recriado' (uma transação, um commit):
- calendar_events.google_event_id = created['id']; google_html_link = created.get('htmlLink') (None se não vier — o sync preenche, routes.py:2305); source = 'platform'; coluna da marca = NULL (via helper de desmarcar da frente da marca).
- EventLog(actor_name=actor.name, actor_role=', '.join(papéis), message='Devolveu o evento ao Google Agenda (estava marcado como sumido desde dd/mm/aaaa).')
- AuditLog via _log_sync('google_returned', event, details='Devolvido ao Google Agenda; novo id <id>; marcado desde <carimbo>', actor=actor.name, actor_role=...) chamado ANTES da troca do id.
- notificacoes_ops.marcar_lidas_por_entidade(<entity_type do aviso>, event.id, kind=<kind do sumiço>) — nomes são da frente do sino.
Imports de Google SEMPRE tardios e por atributo do módulo (from app.calendar import service as gcal; gcal.insert_event(...)) — ver DG-8.

**Pontos de toque.**
- app/calendar/sumico_ops.py (novo; módulo compartilhado com a frente da marca)
- app/calendar/cancel_ops.py:17-45, 272, 299-313 (molde: exceção própria, carimbo naive SP, EventLog + _log_sync + commit)
- app/formularios/formularios_ops.py:172-186 (molde do FOR UPDATE + populate_existing)
- app/calendar/routes.py:393-414 (_log_sync — reuso por import tardio; AuditLog.action é String(60), models.py:598)
- app/calendar/routes.py:57 (CALENDAR_ID — import tardio)
- app/models.py:244-248 (google_event_id unique/not null, google_html_link), :300 (source), :568-581 (EventLog: actor_role String(60))
- app/notificacoes/notificacoes_ops.py:362-378 (marcar_lidas_por_entidade — reuso, sem commit)
- app/calendar/service.py:93-132 (load_credentials abre app_context aninhado; com flask-sqlalchemy 3.1.1, requirements.txt:5, a sessão é outra e o commit do save_token não solta o bloqueio)

**Riscos.**
- A linha do evento fica bloqueada enquanto o Google responde; se o Google pendurar (timeout padrão do cliente ~60 s), um PATCH no mesmo evento espera junto. Mesmo risco já aceito na criação a partir de formulário (298).
- Depende de nomes de outras frentes: coluna da marca (proposta nos achados: google_missing_since), helper de desmarcar, kind/entity_type do sino. O plan precisa fixar esses nomes num lugar só.
- actor_role é String(60): usuário com muitos papéis pode estourar — mesmo padrão já usado em cancel_ops.py:302; não agravar.

**Verify.** Cenário 10 (com a trava desligada no processo e dublês — DG-8): antes, editar título e data do evento marcado (cenário 14) para provar 'dados atuais'. POST como Superadmin → 200, resultado='recriado'. Por CONEXÃO SEPARADA: google_event_id = id do dublê; google_html_link = link do dublê; source='platform'; marca NULL; 1 EventLog novo com o nome do Superadmin; 1 AuditLog action='google_returned' cujo detail contém 'gcal:<id velho>' e o id novo; notificações do sumiço daquele evento com read_at preenchido; venda, EventPayment, EventContract e EventRole com as mesmas contagens de antes. Dublê de insert chamado exatamente 1 vez, com título/início/fim/local/descrição iguais aos do banco. Cenário 10f (idempotência): segundo POST no mesmo evento → 409 nao_marcado e o dublê continua com 1 chamada.

**Revisão adversarial: parcial.** Módulo `*_ops`, imports tardios, `FOR UPDATE` com `populate_existing` e `_log_sync` antes da troca do id sustentam. Conferi: nenhum relacionamento de `CalendarEvent` é `lazy='joined'`, então o `FOR UPDATE` não esbarra em outer join; e com flask-sqlalchemy 3.1.1 o `app_context` aninhado de `load_credentials`/`save_token` usa outra sessão, logo o commit do token não solta o bloqueio. Quatro problemas: (1) O carimbo do EventLog copia um defeito. `_serialize_logs` trata `created_at` sem fuso como UTC e converte para São Paulo; o `agora` do cancel_ops é horário de São Paulo sem fuso, então o histórico mostraria a devolução 3 h antes do que aconteceu. O aceite da História 3 pede 'quem devolveu e quando'. O cancel_ops tem o mesmo defeito e ninguém viu porque o cancelamento tem zero uso. (2) '1 função de ~120 linhas' viola o Princípio II (funções de ~30 linhas, até 3 níveis). (3) Depois do bloqueio a proposta revalida só a marca; um cancelamento concorrente, ou um id já trocado, passaria e o sistema recriaria no Google um evento cancelado. (4) `actor_role` é `String(60)` em EventLog e AuditLog; aqui o estouro viria DEPOIS do insert no Google e cairia no ramo de compensação. É o mesmo padrão já usado na criação, mas aqui custa um evento órfão.

**Emenda.** (1) Não passar `created_at` no EventLog (vale o default `datetime.utcnow` do modelo) ou passar `datetime.now(tz=TZ)` com fuso, como o event_ops faz. Registrar no plan que o cancel_ops tem o mesmo defeito, para a frente do cancelamento. O verify confere o `ts` serializado, não só a existência da linha. (2) Quebrar em funções de até ~30 linhas: `_validar`, `_exigir_ambiente_liberado`, `_bloquear_e_revalidar`, `_recriar_no_google`, `_registrar_devolucao_google`, mais a orquestradora. (3) Depois do bloqueio, revalidar todas as pré-condições: marca presente, `cancelled_at` nulo, `google_event_id` igual ao consultado, datas presentes. (4) Montar EventLog e a parte local antes do Google e dar `db.session.flush()`, com `actor_role[:60]`; depois do insert ficam só a troca de id, link e origem, o AuditLog e o commit. Assim, falha de banco previsível acontece antes da escrita externa. (5) Opcional: a view mapeia `codigo` para status, em vez de a exceção do núcleo carregar o status HTTP.

**Evidência da revisão.** app/api/agenda_read.py:210-214 (sem fuso = UTC); app/models.py:577-579, :594 (actor_role String(60), default utcnow), :328-370 (sem lazy joined); app/calendar/cancel_ops.py:272, :299-305 (horário de SP sem fuso); app/calendar/event_ops.py:499, :594, :963 (convenção com fuso); app/calendar/service.py:98-104, :128-130; requirements.txt:5; .specify/memory/constitution.md:43-44; specs/303-sync-nao-apaga-venda/spec.md:183-185

## DG-3 — (b) O que exatamente é enviado ao Google na recriação — dia inteiro, Meet, extendedProperties, convidados?

**Decisão.** Reusa insert_event com os mesmos cinco campos que _push_cabecalho_ao_google já envia (event.title como está no banco, start_at, end_at, description or '', location or ''). Sem conference_request_id (Meet é só de venda virtual, que nunca é marcada), sem attendees e sem extendedProperties — em especial NUNCA a chave manto_kind, que faria o sync pular o evento para sempre. insert_event ganha um parâmetro opcional all_day: bool = False; o núcleo passa True quando start_at e end_at são ambos meia-noite e end_at > start_at (é assim que o sync grava evento de dia inteiro: parse_event_datetime devolve meia-noite naive e o fim exclusivo do Google). Evento sem start_at ou sem end_at é recusado (sem_data) antes de qualquer chamada.

**Porquê.** O título do banco já carrega o prefixo '(TIPO)' (event_ops.py:927, 1044) e é o que o sync lê de volta; mandar o mesmo conjunto de campos do push de edição garante que o primeiro sync depois da devolução não detecte mudança (_detect_changes, routes.py:2093-2118) e não notifique elenco. Hoje insert_event sempre manda dateTime (service.py:242-247): um evento de dia inteiro, inclusive de vários dias, voltaria como bloco de 24/72 h atravessando a grade da equipe. O parâmetro é aditivo, default False, e não muda nenhum dos 6 chamadores atuais. insert_event não passa sendUpdates nem attendees, o que cumpre a Premissa 'recria sem convidados'. end_at nulo quebraria em end_dt.isoformat(); em dados reais só acontece em evento corrompido.

**Alternativas rejeitadas.** (1) Mandar sempre com hora (não tocar service.py) — rejeitado: muda a aparência do evento na agenda da empresa e a spec pede 'data e horário atuais'. (2) Usar upsert_task_event, que já faz dia inteiro — rejeitado: ele força transparency, lembrete, sendUpdates='all' e foi feito para prazo de figurino (service.py:291-359). (3) Inventar fim = início + 1 h quando end_at é nulo — rejeitado: inventa dado; a edição local (que não escreve no Google enquanto marcado, FR-008) resolve. (4) Gravar extendedProperties.private.manto_event_id para reconhecer o evento depois — rejeitado: nada o leria nesta feature. (5) 'Desapagar' o evento antigo com patch status=confirmed (mantendo o id) — rejeitado: não é comportamento documentado, falha depois que a lixeira expira, e a spec (FR-012, cenário 10) já fixou id novo.

**Contrato.** def insert_event(calendar_id, title, start_dt, end_dt, description='', location='', conference_request_id=None, *, all_day: bool = False) -> dict
- all_day=True → body['start'] = {'date': start_dt.date().isoformat()}; body['end'] = {'date': end_dt.date().isoformat()} (fim já é exclusivo no banco).
- all_day=False → corpo idêntico ao de hoje.
Regra no núcleo: dia_inteiro = start_at.time() == time(0,0) and end_at.time() == time(0,0) and end_at > start_at.
Chamada: gcal.insert_event(CALENDAR_ID, event.title, event.start_at, event.end_at, description=event.description or '', location=event.location or '', all_day=dia_inteiro).

**Pontos de toque.**
- app/calendar/service.py:217-263 (insert_event: acrescentar all_day keyword-only; corpo com start/end {'date': ...} quando True)
- app/calendar/service.py:194-214 (parse_event_datetime — prova de como o dia inteiro chega ao banco)
- app/calendar/event_ops.py:541-558 (_push_cabecalho_ao_google — mesmos campos; não mexer)
- app/calendar/routes.py:2168-2181, 2212-2213 (_is_manto_task_item: por que não usar manto_kind)
- app/calendar/routes.py:2093-2118 (_detect_changes — não pode disparar depois da devolução)
- app/marketing/virtuais_ops.py:1178-1191 (único uso de Meet; precedente de ler htmlLink da resposta)

**Riscos.**
- Evento com hora marcado exatamente 00:00→00:00 do dia seguinte seria recriado como dia inteiro; no banco os dois são indistinguíveis e o resultado depois do sync é o mesmo.
- Cor, lembretes, anexos e convidados que o evento tinha no Google se perdem (Premissa da spec).
- Título com segmento reservado (ex.: '+ Coordenador') vai ao Google como está e o sync o limpa na volta (routes.py:2233) — comportamento de hoje.

**Verify.** Cenário 10b: evento marcado com start_at 00:00 do dia D e end_at 00:00 de D+2 → o dublê de insert recebe all_day=True. No cenário 10 (evento com hora) recebe all_day=False (ou ausente). Conferir que o dublê NÃO recebe conference_request_id. Cenário 10i (DEVE falhar): evento marcado com end_at NULL → 409 sem_data, dublês de consulta e insert com 0 chamadas. Teste unitário do corpo: chamar o insert_event REAL com service.build trocado por um falso que captura o body e conferir 'date' × 'dateTime'.

**Revisão adversarial: sim.** Sustenta. `insert_event` sempre manda `dateTime`; o parâmetro keyword-only `all_day` é aditivo e nenhum chamador quebra. A regra meia-noite→meia-noite com fim maior que o início é segura: `_build_start_end` nunca produz 00:00→00:00 do dia seguinte (fim igual ao início fica no mesmo dia e é rejeitado), então só evento de dia inteiro importado chega ao banco assim. O título do banco já carrega o prefixo do tipo, e os cinco campos são os mesmos de `_push_cabecalho_ao_google`, então o primeiro sync não detecta mudança. Duas correções pequenas: são 5 pontos de chamada, não 6; e `end_at` menor que `start_at` (dado corrompido) iria ao Google, voltaria 400 e viraria `google_recusou` com 'tente de novo', que não se resolve tentando.

**Emenda.** Corrigir a contagem para 5 chamadores. Incluir `end_at < start_at` na recusa `sem_data`, com a mensagem 'data ou horário inválidos', antes de qualquer chamada. No teste do corpo do insert, trocar `cal_service.build` e AFIRMAR a troca antes de restaurar um `load_credentials` falso, com `try/finally` próprio.

**Evidência da revisão.** app/calendar/service.py:203-205, :217-263; app/calendar/routes.py:146-150 (`_build_start_end`), :2093-2118, :2168-2181; app/calendar/event_ops.py:550-558, :927, :1044, :1642; chamadores: event_ops.py:1642, routes.py:2584, routes.py:4037, app/api/agenda_write.py:812, app/marketing/virtuais_ops.py:1179

## DG-4 — (b) Consultar o id velho antes de inserir: o que fazer em cada resposta?

**Decisão.** Antes do insert, o núcleo consulta o google_event_id atual pela função de três estados que a frente do sync cria para a FR-002/FR-003 (presente / ausente / inconclusivo). PRESENTE (existe e não está 'cancelled'): não insere nada; chama o mesmo caminho de reaparecimento da FR-006 usado pelo ciclo (desmarca, aplica o item do Google, registra 'reapareceu'), com o ator no histórico, e responde resultado='reapareceu'. AUSENTE (404/410 ou status 'cancelled'): segue para o insert. INCONCLUSIVO (erro, timeout, sem credencial, falha de refresh): não insere, marca intacta, 502 google_inconclusivo.

**Porquê.** Se o evento voltou da lixeira entre o último ciclo (até 10 min atrás) e o clique, inserir criaria um segundo evento no Google; o antigo, ainda vivo, seria importado como evento novo e vazio no ciclo seguinte. Reusar a função de três estados e o caminho de reaparecimento evita uma segunda definição de 'ausência confirmada' (fetch_single_event devolve None para tudo, service.py:181-191, e não olha status). Em resposta inconclusiva, o insert muito provavelmente falharia também; e, se passasse, criaria duplicata sem saber. No ramo 'reapareceu' vale o Google, como no ciclo (padrão já adotado na síntese, item 12).

**Alternativas rejeitadas.** (1) Inserir sempre, sem consultar — rejeitado: duplicata certa no caso de restauração da lixeira. (2) Usar fetch_single_event como está — rejeitado: None serve para 404 e para rede caída, e um evento apagado volta do events.get com status 'cancelled' (seria lido como 'presente'). (3) Inconclusivo → tentar o insert assim mesmo — rejeitado: na dúvida o evento fica como está (mesmo princípio da FR-003). (4) No ramo 'reapareceu', empurrar os dados do sistema por cima do Google — rejeitado: abriria uma segunda semântica para o reaparecimento; a do ciclo é 'vale o Google'.

**Contrato.** Dependência (nome final é da frente do sync): consultar_evento_google(google_event_id: str) -> tuple[Literal['presente','ausente','inconclusivo'], dict | None]
Dependência: caminho único de reaparecimento da FR-006 aceitando actor opcional (ciclo = Sistema; botão = Superadmin).
Esta frente exige só: três estados distintos; 'cancelled' = ausente; exceção de credencial/refresh = inconclusivo, nunca exceção solta.

**Pontos de toque.**
- app/calendar/service.py:181-191 (fetch_single_event — não muda; tem dois outros consumidores: virtuais_ops.py:1679 e routes.py:4203)
- função nova de consulta em três estados e função de desmarcar por reaparecimento (FR-002/FR-003/FR-006) — definidas pela frente do sync; esta frente só consome
- app/calendar/routes.py:2184-2406 (sync_events — é o que o caminho de reaparecimento aplica; commita por conta própria em :2352/:2358/:2406)

**Riscos.**
- Janela de milissegundos entre a consulta e o insert em que o id velho pode reaparecer — aceita.
- Se o id velho for restaurado da lixeira DEPOIS da devolução, nenhuma linha tem mais aquele id e o sync o importa como evento novo e vazio (duplicata visível na agenda). O id velho fica no AuditLog; entra em docs/05 como risco conhecido.
- No ramo 'reapareceu', evento de origem google_calendar editado no sistema enquanto marcado é sobrescrito pelo Google e tem o elenco reconciliado pelo título antigo, com e-mail de remoção (routes.py:2361-2392) — risco já aceito para o ciclo; aqui o gatilho passa a ser também o clique.

**Verify.** Cenário 10c: dublê de consulta devolve 'presente' com item do id velho → 200 resultado='reapareceu'; dublê de insert com 0 chamadas; google_event_id inalterado; marca NULL; histórico com 'reapareceu'. Cenário 10e: dublê devolve 'inconclusivo' → 502 google_inconclusivo; insert 0 chamadas; marca e id intactos por conexão separada. O item do dublê de 'presente' precisa de start/end/summary válidos e de dublês de Geocoding/Distance Matrix se o local mudar (routes.py:2319-2335).

**Revisão adversarial: parcial.** Consultar antes de inserir e tratar inconclusivo como 'não insere' sustentam: `fetch_single_event` devolve `None` para tudo e não olha `status`. O problema é o ramo 'presente'. A FR-012 promete recriar 'com título, data, horário, local e descrição ATUAIS', e a FR-008 deixa a equipe editar o evento enquanto marcado. No ramo 'reapareceu' o clique do Superadmin aplica o Google por cima: `sync_events` sobrescreve os cinco campos com os dados de quando o evento foi apagado, avisa o elenco aceito da 'mudança' de data (e-mail real em produção) e reconcilia o elenco pelo título antigo. A tela diz só 'a marca foi retirada'. É perda silenciosa do que foi editado, numa ação cujo contrato é o oposto. A síntese adotou 'vale o Google' para o reaparecimento AUTOMÁTICO; a spec não decide isso para o botão.

**Emenda.** Registrar no plan como decisão explícita (não está na spec) e escolher uma das duas: (a) recomendado: no ramo 'presente', comparar os cinco campos do item com o banco. Se iguais, só desmarca. Se diferentes, chamar `_push_cabecalho_ao_google(event)` no id velho (função que já existe) e só então desmarcar pelo caminho único; falha do push responde 502 e a marca continua. Cumpre a FR-012 e não dispara aviso nem reconciliação pelo título antigo. (b) mínimo: manter 'vale o Google', mas a resposta traz `dados_do_google_aplicados: true` quando houve diferença, a mensagem diz 'O evento já tinha voltado ao Google Agenda; título, data e local voltaram ao que estava lá — confira', e o EventLog registra os campos sobrescritos. Nos dois casos o cenário 10c ganha a variante 'editado enquanto marcado'.

**Evidência da revisão.** specs/303-sync-nao-apaga-venda/spec.md:379-382, :472-474; app/calendar/routes.py:2286-2295 (sobrescreve), :2340-2342 (avisa o elenco), :2361-2392 (reconcilia e manda e-mail de remoção); app/calendar/event_ops.py:541-558; app/calendar/service.py:181-191

## DG-5 — (b) Como a devolução convive com a guarda de 5 minutos do sync_events e o que acontece se o Google recusar (ou o commit falhar)?

**Decisão.** A guarda de 5 minutos não muda: o núcleo commita id novo, link e desmarcação imediatamente depois do insert, sem nenhuma consulta pesada no meio (log, auditoria e notificação são só INSERT/UPDATE locais preparados na mesma transação). Se o insert levantar qualquer exceção ou voltar sem 'id': rollback (solta o bloqueio), a marca e o id velho ficam como estavam, grava-se um AuditLog 'google_return_failed' com o texto do erro (commit próprio), e sobe DevolverAoGoogleError 502 google_recusou com mensagem fixa em pt-BR (sem o erro bruto). Se o insert passar e o COMMIT falhar: rollback e uma tentativa de apagar do Google o evento recém-criado (delete_event no id novo, best-effort, erro só logado), depois 502.

**Porquê.** A guarda (routes.py:2190-2208) pula item do Google com menos de 5 minutos que ainda não tem linha local — é exatamente o intervalo entre o insert e o commit da devolução, a mesma corrida da criação (254). Depois do commit a linha existe com o id novo e o sync segue pelo ramo de atualização, que não encontra diferença. O Princípio V proíbe erro bruto na tela; o cancel_ops.py:286 devolve '{exc}' e isso não deve ser copiado. O delete compensatório evita que uma falha de banco depois do insert deixe um evento órfão no Google, que 5 minutos depois seria importado como evento novo e vazio — e o clique seguinte do Superadmin criaria um terceiro.

**Alternativas rejeitadas.** (1) Gravar o id novo antes do insert, com id gerado pelo cliente (o Google aceita id próprio e responde 409 em repetição) — rejeitado: daria idempotência também na falha de commit, mas muda a assinatura de insert_event e introduz regra de formato de id; o bloqueio + delete compensatório cobre o caso com menos peça nova. (2) Estender a guarda para 'pular item cujo título/data batem com evento marcado' — rejeitado: heurística dentro do sync, fora do mínimo. (3) Falha do Google registrada também no EventLog — rejeitado: poluiria o histórico do evento a cada tentativa; a auditoria basta e a FR-023 pede rastro do que aconteceu, não da tentativa. (4) Falha do Google como aviso com 200 — rejeitado: a FR-012 diz 'a marca continua e a tela diz que não deu'.

**Contrato.** Sequência no ramo 'recriado': lock → created = gcal.insert_event(...) → _log_sync('google_returned', ...) → troca de campos → EventLog → marcar lidas → db.session.commit().
Falha do insert: db.session.rollback(); _log_sync('google_return_failed', event, details=str(exc)[:300], actor=..., actor_role=...); db.session.commit(); raise DevolverAoGoogleError('google_recusou', <msg fixa>, 502).
Falha do commit: db.session.rollback(); try: gcal.delete_event(CALENDAR_ID, novo_id) except Exception: logger.exception(...); raise DevolverAoGoogleError('google_recusou', <msg fixa>, 502).

**Pontos de toque.**
- app/calendar/routes.py:2190-2208 (guarda de 5 min — sem mudança)
- app/calendar/routes.py:2247, 2284-2305 (ramo de atualização que o sync segue depois do commit)
- app/calendar/service.py:362-368 (delete_event — usado só na compensação)
- app/api/agenda_write.py:811-843 (precedente: 502 na falha do Google e log de 'evento Google órfão' na criação)
- app/calendar/cancel_ops.py:282-286 (contraexemplo: expõe {exc} ao usuário)

**Riscos.**
- Se o delete compensatório também falhar, sobra um órfão no Google que o sync importa depois de 5 minutos como evento vazio; fica no log de erro com o id.
- Ciclo do sync rodando em outro worker no mesmo instante: a conferência dos marcados lê o id velho, confirma ausência e não escreve nada — inofensivo; só vira duplicata no caso duplo 'restaurado da lixeira no mesmo segundo'.

**Verify.** Cenário 10d (Google recusa): dublê de insert levanta exceção → 502 google_recusou; por conexão separada marca, google_event_id e google_html_link idênticos aos de antes; nenhum EventLog de devolução; 1 AuditLog 'google_return_failed'; a mensagem da resposta NÃO contém o texto da exceção do dublê. Cenário 10g (guarda e pós-commit): depois do cenário 10, chamar sync_events([{id: <id novo>, created: agora em ISO, summary: título do banco, start/end iguais}]) → continua 1 linha com aquele google_event_id, sem marca, sem EventLog 'Evento criado', sem notificação de mudança ao elenco. Variante: sync_events com um item de id desconhecido e created=agora → nenhuma linha criada (prova que a guarda continua valendo).

**Revisão adversarial: parcial.** A guarda de 5 minutos cobre o intervalo entre insert e commit, e a mensagem fixa cumpre o Princípio V. Três lacunas: (1) Falta o risco 'o Google criou, mas a resposta se perdeu'. `build()` não recebe timeout em nenhuma chamada, então vale o padrão do cliente (~60 s). Nesse caso o núcleo faz rollback, mantém a marca e a tela diz 'tente de novo em instantes'; o órfão é importado 5 minutos depois como evento novo e vazio, e o segundo clique cria outro. (2) O delete compensatório da falha de commit é código sem cenário de verify, o que o Princípio VIII trata como não verificado. A causa provável dessa falha (coluna estourada) some com o flush antes do Google da DG-2. (3) Uma requisição pode segurar a linha por mais de 60 s (consulta, mais refresh do token, mais insert). Não derruba nada (gunicorn gthread com timeout 120, proxy com 180 s de inatividade), mas o plan fala em '~1 s'.

**Emenda.** (1) Listar o risco do timeout com sucesso. A mensagem de `google_recusou` passa a ser 'O Google Agenda não confirmou a criação. A marca continua. Antes de tentar de novo, confira na Agenda se o evento apareceu.' O AuditLog `google_return_failed` guarda o tipo da exceção. (2) Criar o cenário 10j: dublê de insert ok e `db.session.commit` trocado para falhar uma vez; esperado 502, `delete_event` chamado 1 vez com o id novo, marca e id velho intactos por conexão separada. Ou retirar a compensação e registrar o órfão como risco. (3) Aplicar o flush antes do Google (DG-2, item 4). (4) Escrever no plan o teto real do bloqueio. Id determinístico gerado pelo cliente não compensa: no retry depois de 5 minutos o sync já importou o órfão e o commit bateria na unicidade de `google_event_id`.

**Evidência da revisão.** app/calendar/routes.py:2190-2208, :2247-2305; app/calendar/service.py:139, :186, :241 (`build` sem timeout); render.yaml:31; frontend/server.js:619, :688; app/models.py:244; .specify/memory/constitution.md:155-166

## DG-6 — (b) Depois de devolvido, o sync pode reconciliar o elenco pelo título e mandar e-mail de remoção?

**Decisão.** No ramo 'recriado', o núcleo grava source='platform' no evento. A partir daí o sync continua atualizando título, data, local e descrição pelo Google, mas não apaga nem recria personagens a partir do título.

**Porquê.** Enquanto marcado, o evento fica dias fora do alcance do sync e a equipe continua mexendo na escala (casting_ops.py:434 cria personagem sem tocar o título; o 'Editar tudo' reconcilia elenco e título separadamente, event_ops.py:915-927). Para evento de origem google_calendar, o primeiro sync depois da devolução apagaria todo personagem que não está no título e mandaria e-mail de remoção ao talento (routes.py:2361-2392) — justamente a escala que fez o evento ser preservado. 'platform' é o valor que o sistema já dá a todo evento cujo registro no Google foi criado por ele (routes.py:3351; virtuais_ops.py:1265), e é o que a devolução faz. O único outro leitor de source é um texto de ajuda da aba Comercial para evento importado sem venda (ComercialSection.tsx:573, 723-728).

**Alternativas rejeitadas.** (1) Não mexer em source e registrar o risco — rejeitado: o efeito é e-mail a pessoa de verdade, disparado por uma ação cujo objetivo é preservar o evento. (2) Recusar a devolução quando houver personagem fora do título — rejeitado: obrigaria o Superadmin a consertar título à mão antes de resolver uma faixa que pede decisão rápida. (3) Reescrever o título a partir do elenco antes de inserir — rejeitado: a spec manda recriar com o título atual.

**Contrato.** No commit da devolução: event.source = 'platform'. Não se aplica ao ramo 'reapareceu' (lá vale o Google, como no ciclo).

**Pontos de toque.**
- app/calendar/routes.py:2350-2353 (ramo 'platform' do sync: commita e pula a reconciliação)
- app/calendar/routes.py:2361-2392 (reconciliação pelo título + send_removal_email)
- app/calendar/routes.py:3351 e app/marketing/virtuais_ops.py:1265 (quem já nasce 'platform')
- app/api/agenda_read.py:943 e frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx:573, 723-728 (único consumidor de venda.source)
- app/models.py:300 (coluna source, String(20), default 'google_calendar')

**Riscos.**
- Para o evento devolvido, acrescentar um personagem editando o título direto no Google deixa de criar a vaga — comportamento que todo evento criado pela plataforma já tem.
- Evento devolvido sem venda perde o lembrete 'Evento importado do Google, sem venda' na aba Comercial.

**Verify.** Dentro do cenário 10g: o evento do cenário 10 tem uma role de personagem existente (talent_id preenchido, SEM inventar character_name — assumir role real, regra do CLAUDE.md §4) cujo nome não está no título; depois de sync_events([item do id novo]) a role continua lá e o capturador de e-mail não recebeu e-mail de remoção. Prova por mutação: sem a linha source='platform', o mesmo cenário apaga a role.

**Revisão adversarial: parcial.** O fato técnico está certo: o sync só pula a reconciliação quando `source == 'platform'`, e os únicos leitores de `source` são o sync e o texto de ajuda da aba Comercial. Três ressalvas: (1) É uma mudança permanente de comportamento que o dono não decidiu. A História 3 diz que o evento 'volta a ser sincronizado normalmente'; para evento nascido no Google, 'normal' inclui 'acrescentei + ELSA no título pelo Google e a vaga apareceu'. Depois da devolução isso para de funcionar em silêncio, e a origem não aparece em tela nenhuma. (2) O risco que motiva a troca é mais estreito que o descrito: fora da marca, o sync já apaga em até 10 minutos a vaga de personagem que não está no título, então a equipe já precisa manter o título. O risco novo é só a vaga criada durante a marca sem ajuste do título. (3) A justificativa 'todo evento criado pela plataforma já é platform' é falsa para ensaio, que nasce com o default `google_calendar`. E a nota de verify manda usar vaga com `talent_id` preenchido, contra a regra do CLAUDE.md §4 (assumir vaga com `talent_id IS NULL`).

**Emenda.** (1) Trocar a origem só quando for necessário: antes do insert, calcular com os helpers do próprio sync (`parse_characters`, `strip_role_prefix`, `_is_reserved_title_name`) se existe vaga não-extra fora do título atual. Se existe, `source='platform'` e o EventLog diz 'O elenco deste evento passa a ser mantido pelo sistema: personagem acrescentado no título pelo Google não cria vaga'. Se não existe, a origem fica como está, e 'sincronizado normalmente' vale ao pé da letra. Se o plan preferir a troca incondicional, registrá-la como desvio deliberado (plan, docs/04 e a mesma linha no EventLog) e levar ao dono. (2) Verify: a vaga fora do título usa um Talent descartável criado pelo próprio verify, com e-mail falso; ou `talent_id` nulo para provar 'a vaga sobrevive', com o e-mail de remoção provado à parte pelo capturador. Nunca talento real. (3) Corrigir a justificativa sobre o ensaio.

**Evidência da revisão.** app/calendar/routes.py:2350-2353, :2361-2392, :3351, :2585-2594; app/calendar/event_ops.py:1643-1652 (ensaio sem source); app/calendar/casting_ops.py:434; app/api/agenda_read.py:943; frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx:573, :723-728; specs/303-sync-nao-apaga-venda/spec.md:166-167; CLAUDE.md (§4, regra do EventRole)

## DG-7 — (c) Princípio XIV: estender CALENDAR_SUPPRESS_INVITES ou criar uma trava nova para escrita de evento de show?

**Decisão.** Trava nova, no mesmo molde: função _suppress_calendar_event_writes() em app/config.py e chave Config.CALENDAR_SUPPRESS_EVENT_WRITES. Default derivado do host do banco (localhost, 127.0.0.1 ou sqlite = travado); CALENDAR_SUPPRESS_EVENT_WRITES=true trava em qualquer ambiente; CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true é o escape. Em produção não precisa de variável nenhuma no painel. Quem consulta a trava é só o núcleo da devolução, antes de qualquer chamada ao Google; ambiente travado responde 409 google_travado e não lê nem escreve na agenda. As escritas antigas de evento de show (criar, editar, excluir, cancelar, ensaio, venda virtual) NÃO passam a consultar a trava nesta feature: viram dívida no docs/05, já com o nome da chave que devem adotar.

**Porquê.** CALENDAR_SUPPRESS_INVITES tem semântica de 'convite a pessoa' e a docstring diz expressamente que os eventos de show não passam por ela (config.py:133-135); o seu escape, CALENDAR_ALLOW_LOCAL_INVITES, passaria a liberar duas coisas de risco diferente de uma vez (convite no e-mail pessoal de alguém × evento na agenda da empresa). Uma chave própria, com nome genérico de 'escrita de evento', é a que as escritas antigas poderão adotar depois sem renomear nada. A constituição pede a trava derivada do host com escape *_ALLOW_LOCAL_* no mesmo commit (XIV) e default real sem env (III/XIV) — o molde existente cumpre os dois. Pôr a checagem dentro de service.insert_event travaria também a criação de evento e de ensaio no ambiente local, mudança de comportamento das escritas antigas que a FR-024 mandou deixar como dívida.

**Alternativas rejeitadas.** (1) Reusar CALENDAR_SUPPRESS_INVITES — rejeitado pelos motivos acima. (2) Checar dentro de service.insert_event/update_event/delete_event — rejeitado: é a quitação da dívida, não o mínimo desta feature; quebraria o fluxo local de criar evento e os verifies antigos que dependem dele. (3) Ambiente travado simula sucesso com id falso — rejeitado: grava mentira no banco (id que não existe no Google) e o próximo sync local marcaria o evento de novo; a regra do projeto é 'localhost = não escreve', e a tela já tem o estado 'não deu'. (4) Checar a trava só antes do insert, deixando a consulta do id velho rodar — rejeitado: ambiente travado sem nenhum I/O externo é mais simples de provar.

**Contrato.** app/config.py:
def _suppress_calendar_event_writes() -> bool:
    if os.getenv('CALENDAR_SUPPRESS_EVENT_WRITES', '').lower() == 'true': return True
    if os.getenv('CALENDAR_ALLOW_LOCAL_EVENT_WRITES', '').lower() == 'true': return False
    db_url = _db_url(); return 'localhost' in db_url or '127.0.0.1' in db_url or db_url.startswith('sqlite')
class Config: CALENDAR_SUPPRESS_EVENT_WRITES = _suppress_calendar_event_writes()
Núcleo: if current_app.config.get('CALENDAR_SUPPRESS_EVENT_WRITES', True): raise DevolverAoGoogleError('google_travado', ..., 409)  — ausência da chave = travado.

**Pontos de toque.**
- app/config.py:121-142 (molde _suppress_calendar_invites; função nova logo abaixo)
- app/config.py:233-236 (Config.CALENDAR_SUPPRESS_INVITES; chave nova logo abaixo)
- app/figurino/producao_ops.py:321-335 (precedente de núcleo lendo current_app.config para a trava)
- DEVELOPMENT.md:139 (tabela de variáveis: linha nova CALENDAR_*_EVENT_WRITES)
- .env.example:29-30 (comentário da trava de e-mail; acrescentar a do calendário)
- docs/01_SISTEMA_E_BANCO.md:404-405 (onde a trava de convite está descrita; citar a nova)
- docs/05_DIVIDA_TECNICA.md (dívida nova: escritas antigas sem trava — routes.py:332, 2584, 2652, 2689, 4037; agenda_write.py:812; event_ops.py:550, 1642, 1683, 1704; cancel_ops.py:283; virtuais_ops.py:1179; figurino/producao_ops.py delete_producao)

**Riscos.**
- O escape CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true num processo local cria evento de verdade na agenda da empresa, e o sync da PRODUÇÃO o importa como evento novo cinco minutos depois. A documentação precisa dizer isso com todas as letras.
- O caminho feliz do botão não pode ser conferido na tela local sem o escape; a conferência de tela local cobre diálogo, carregando e a mensagem de erro (trava), e o sucesso fica provado pelo verify com dublê e pelo primeiro uso real em produção.
- As escritas antigas continuam escrevendo no Google real a partir do manto_local — nada piora, mas a dívida passa a ter nome.

**Verify.** Cenário 10a (DEVE falhar, roda ANTES de desligar a trava): o verify confere app.config['CALENDAR_SUPPRESS_EVENT_WRITES'] is True (manto_local = localhost); POST como Superadmin → 409 codigo=google_travado; dublês de consulta E de insert com 0 chamadas; marca, id e histórico intactos por conexão separada. Cenário de config (molde do verify_269b.py:95-150, recarregando app.config em subprocesso/import isolado): banco remoto sem env → False; localhost → True; localhost + CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true → False; remoto + CALENDAR_SUPPRESS_EVENT_WRITES=true → True.

**Revisão adversarial: sim.** Sustenta. A docstring de `_suppress_calendar_invites` exclui os eventos de show, e a FR-024 deixa a escolha ao plan. Trava derivada do host com escape `*_ALLOW_LOCAL_*` e default real sem env cumpre o Princípio XIV; ler `current_app.config` no núcleo tem precedente no figurino; não pôr a checagem dentro de `service.insert_event` respeita a FR-024, que manda as escritas antigas virarem dívida. Só falta documentação: os touchpoints esquecem quatro lugares que afirmam que as travas 'cobrem só e-mail e convite'.

**Emenda.** Acrescentar aos touchpoints: CLAUDE.md:98, .claude/skills/manto-verify/SKILL.md:23, DEVELOPMENT.md:105 e docs/01_SISTEMA_E_BANCO.md:1866, além dos já listados. Em todos deixar claro que a trava nova cobre SÓ a devolução e que criar, editar, excluir e cancelar evento de show continuam escrevendo no Google real a partir do manto_local. No comentário da chave em config.py, dizer que o escape local cria evento de verdade que a PRODUÇÃO importa 5 minutos depois.

**Evidência da revisão.** app/config.py:121-142, :233-236; app/figurino/producao_ops.py:327-330; .specify/memory/constitution.md:228-242; specs/303-sync-nao-apaga-venda/spec.md:597-600; CLAUDE.md:98; DEVELOPMENT.md:105; .claude/skills/manto-verify/SKILL.md:23

## DG-8 — (c) O que o verify substitui para nunca ler nem escrever na agenda real, já que precisa desligar a trava para exercitar o sucesso?

**Decisão.** Três camadas, nesta ordem, no topo do verify_303.py: (1) corta-tudo: cal_service.load_credentials = lambda: None — qualquer função real do service que escape de um dublê levanta RuntimeError('Google não conectado') ou devolve None, sem rede; (2) dublês contadores para cal_service.insert_event, update_event, delete_event, fetch_events_for_month, fetch_single_event e para a consulta nova de três estados, mais a cópia por nome em cal_routes (insert_event, update_event, delete_event, fetch_single_event, fetch_events_for_month), porque routes.py importa essas funções pelo nome na carga do módulo; (3) a trava só é desligada em processo (app.config['CALENDAR_SUPPRESS_EVENT_WRITES'] = False) dentro de try/finally em volta dos cenários 10–10h, depois de afirmar que cal_service.insert_event é o dublê. O núcleo novo chama o Google sempre por atributo do módulo (gcal.insert_event), com import tardio, para que trocar o atributo em app.calendar.service baste.

**Porquê.** Os verifies anteriores trocam insert_event no service e em routes, mas não update/delete em routes (verify_302.py:102-105; achado G1), e o verify_205 chamaria o Google real depois da 303 (risco 8 da síntese). Um único ponto de corte em load_credentials cobre o que for esquecido: todas as funções do service passam por ele (service.py:135, 162, 183, 238, 276, 324, 364). A trava desligada só em app.config — nunca por variável de ambiente — garante que nenhum outro processo herde o escape.

**Alternativas rejeitadas.** (1) Exportar CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true no ambiente do verify — rejeitado: vaza para qualquer subprocesso e vira hábito. (2) Confiar só nos dublês por função — rejeitado: basta um import por nome esquecido para escrever na agenda da empresa. (3) Dublê do objeto build() do googleapiclient — rejeitado como camada principal: mais frágil que cortar a credencial; serve só no teste unitário do corpo do insert (DG-3).

**Contrato.** Dublê de insert: def _fake_insert(calendar_id, title, start_dt, end_dt, description='', location='', conference_request_id=None, *, all_day=False) -> {'id': f'{PREFIX}g<hex>', 'htmlLink': f'https://calendar.invalid/{PREFIX}<hex>'}; registra cada chamada em lista. Dublê da consulta: dicionário {google_event_id: ('presente'|'ausente'|'inconclusivo', item)} com default 'ausente'. Pré-condições afirmadas em main(): MAIL_SUPPRESS_SEND is True; CALENDAR_SUPPRESS_EVENT_WRITES is True; cal_service.load_credentials() is None.

**Pontos de toque.**
- specs/303-sync-nao-apaga-venda/verify_303.py (novo)
- specs/302-portal-detalhes-do-evento/verify_302.py:99-105 (molde dos dublês)
- app/calendar/routes.py:19-29 (imports por nome que exigem a cópia em cal_routes)
- app/calendar/sync.py:49 (import tardio de fetch_events_for_month a partir do service)
- app/calendar/service.py:93-132 (load_credentials — ponto de corte)
- specs/205-loja-interacoes-virtuais/verify_205.py:782-810 (passaria a consultar o Google real; anotar no plan)

**Riscos.**
- Se a frente do sync puser a consulta de três estados num módulo diferente de app.calendar.service, o verify precisa trocar o atributo lá também — fixar o módulo no plan.
- O cenário de teste unitário do corpo do insert (DG-3) restaura temporariamente um load_credentials falso que devolve um objeto qualquer e troca service.build; precisa de try/finally próprio.

**Verify.** Primeiro bloco do verify, antes de qualquer cenário: afirmar as três pré-condições. Último bloco (finally): restaurar app.config['CALENDAR_SUPPRESS_EVENT_WRITES'] = True antes da limpeza. Em todo cenário de recusa, conferir os contadores dos dublês além do status HTTP.

**Revisão adversarial: parcial.** As três camadas e a trava desligada só em `app.config` sustentam. Conferi: todas as funções do service passam por `load_credentials`, que só é referenciada dentro de service.py, e a lista de cópias por nome em `cal_routes` bate com os imports. O defeito é o corta-tudo `lambda: None`, que falha em silêncio. Se um dublê não for aplicado (atributo no módulo errado), o `fetch_single_event` real devolve `None` e a consulta real de três estados devolve 'inconclusivo'. Esse é exatamente o resultado que o cenário 10e espera, então ele passaria sem exercitar o dublê; o mesmo vale para os '0 chamadas' do 10a. O Princípio VIII chama isso de defeito do verify. O verify_299 já tem o molde melhor, em que `load_credentials` levanta erro.

**Emenda.** Trocar o corta-tudo por um dublê que registra e estoura: `def _fuga(*a, **k): _fugas.append(traceback.format_stack()); raise RuntimeError('verify 303: Google real')`. Atribuir a `cal_service.load_credentials` e, como no verify_299, a cada função real que tenha dublê próprio em outro módulo. A última afirmação do verify é `len(_fugas) == 0`; a função de três estados engole a exceção e devolve 'inconclusivo', por isso o contador é indispensável. Cada cenário afirma o contador do SEU dublê (o 10e exige 1 chamada ao dublê de consulta). Fixar no plan o módulo da consulta de três estados, para o verify trocar o atributo no lugar certo.

**Evidência da revisão.** specs/299-sem-valor-cobrancas/verify_299.py:105-114; specs/302-portal-detalhes-do-evento/verify_302.py:99-105; app/calendar/service.py:135, :162, :183-185, :238-240; app/calendar/routes.py:19-29; app/calendar/sync.py:49; .specify/memory/constitution.md:155-166

## DG-9 — (d) O que o botão 'Devolver ao Google Agenda' faz na tela — confirmação, carregando, erro, sucesso?

**Decisão.** Na faixa da marca do EventHeader (a faixa é da frente da marca), quando flags.can_delete é verdadeiro e o evento não está cancelado, aparecem dois botões: 'Devolver ao Google Agenda' e 'Cancelar e devolver o dinheiro' (este abre o ExcluirEventoDialog, como o 'Analisar e decidir' faz hoje). 'Devolver' abre o ConfirmDialog do @manto/ui, não destrutivo, que explica o que vai acontecer. Confirmar dispara o hook novo useDevolverAoGoogle: o botão gira e o 'Cancelar' do diálogo trava (pending); erro da API aparece DENTRO do diálogo, que fica aberto para nova tentativa; sucesso fecha o diálogo, troca o cache do evento pelo payload devolvido, invalida agenda, busca, faixa e sino, e anuncia pelo aria-live do cabeçalho: 'Evento devolvido ao Google Agenda.' ou, quando resultado='reapareceu', 'O evento já tinha voltado ao Google Agenda — a marca foi retirada.' Nenhuma flag nova: reusa flags.can_delete.

**Porquê.** O ConfirmDialog já traz exatamente os três estados que o Princípio V exige (pending no botão, erro dentro do diálogo, fechar bloqueado durante a ação — confirm-dialog.tsx:11-25, 54-69) e já é exportado (packages/ui/src/index.ts:38). A confirmação se justifica porque a ação escreve na agenda compartilhada da empresa e é decisão do Superadmin; e é o lugar natural para dizer que o evento volta sem convidados e que ensaios apagados não voltam. Reusar can_delete cumpre 'as saídas só aparecem por flag do servidor' sem campo novo: é o mesmo gate do endpoint, com a impersonação aplicada (agenda_read.py:189).

**Alternativas rejeitadas.** (1) Disparar direto no clique, como 'Recusar solicitação' (EventHeader.tsx:393-402) — rejeitado: o erro cairia na linha solta de texto do cabeçalho (:411-412) e não haveria onde explicar 'sem convidados'. (2) Item no menu '⋯ Ferramentas' — rejeitado: a decisão precisa estar na própria faixa da marca (SC-004: resolver sem sair da tela do evento). (3) Flag nova flags.can_devolver_google — rejeitado: duplicaria can_delete. (4) Toast — rejeitado: o cabeçalho já tem o canal aria-live 'anunciar' (:217-220, :408-410).

**Contrato.** export function useDevolverAoGoogle(eventId: number): UseMutationResult<EventoDetalhe, Error, void>
  mutationFn: apiFetch(`/api/events/${eventId}/devolver-ao-google`, { method: 'POST' })
  onSuccess(updated): setQueryData(['event', eventId], updated); invalidate ['agenda'], ['agenda-dia'], ['agenda-search'], ['notificacoes'] e a chave da faixa (definida pela frente da faixa).
ConfirmDialog: title='Devolver ao Google Agenda?'; confirmLabel='Devolver ao Google Agenda'; destructive=false; pending=devolver.isPending; error=devolver.error?.message ?? null.
description: 'O evento será recriado no Google Agenda com o título, a data, o horário, o local e a descrição que estão no sistema agora, e volta a ser sincronizado. Ele volta sem convidados — os convites por e-mail não são reenviados. Ensaios que também foram apagados do Google não voltam: reagende-os pela aba de ensaio.'
Condição de exibição dos dois botões: marca presente no payload && data.flags.can_delete && !event.cancelled_at.

**Pontos de toque.**
- frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:203-215 (hooks e estados), :330-331 (incluir devolver.isPending em 'pendente'), :378-406 (molde da faixa com botões do Superadmin), :408-412 (aria-live e erros)
- frontend/apps/internal/src/lib/eventOps.ts:50-57 (molde useSyncEvent: setQueryData), :141-148 (invalidações do cancelar), após :182 (hook novo)
- frontend/apps/internal/src/lib/agenda.ts (EventoDetalhe: devolucao_google opcional)
- frontend/packages/ui/src/components/confirm-dialog.tsx:11-76 (reuso)
- frontend/apps/internal/src/lib/notificacoes.ts:55 (chave ['notificacoes'] a invalidar)
- app/api/agenda_read.py:189 (flags.can_delete — reuso)

**Riscos.**
- O nome do campo da marca no payload do detalhe é da frente da marca; o botão depende dele.
- Ao reabrir o diálogo depois de um erro, a mensagem antiga continua até nova tentativa — chamar devolver.reset() ao abrir.
- O sucesso não é observável na tela local (trava): ver DG-7.

**Verify.** Conferência de tela (skill manto-conferir-tela), como Superadmin num evento marcado do manto_local: a faixa com os dois botões; o ConfirmDialog aberto com o texto; clicar em confirmar e ver o botão girar e, em seguida, a mensagem da trava DENTRO do diálogo, que continua aberto; como Comercial: faixa sem botões. No verify, o payload de 200 do cenário 10 traz devolucao_google.resultado='recriado' e o evento sem a marca; o de 10c traz 'reapareceu'.

**Revisão adversarial: parcial.** Reusar `ConfirmDialog` e `flags.can_delete` sustenta: o componente é exportado, a flag respeita a impersonação, e mutação não tem retry padrão, então não há POST duplo. Quatro furos: (1) A descrição do diálogo é texto fixo e não mostra O QUE vai ao Google. No caso que motivou a spec (o 1244 estava em 19/09 e foi recriado à mão para 07/11), confirmar recria o evento na data velha, já passada, sem o Superadmin perceber. O próprio contrato do componente pede 'cite o item'. (2) 'Fechar bloqueado durante a ação' não é verdade: o `ConfirmDialog` só desabilita o botão Cancelar; Esc e clique fora chamam `onOpenChange` direto. (3) `anunciar()` apaga a mensagem em 2,2 s; a frase longa do 'reapareceu' some antes de ser lida. (4) Em erro 409 de estado o cache fica velho (ver DG-1).

**Emenda.** (1) A descrição ganha o título e `formatRange(event.start_at, event.end_at)` em destaque ('Será recriado como: <título> — <data e horário>'); quando a data já passou, acrescenta 'Esta data já passou — se o evento mudou de dia, edite a data antes de devolver.' (2) `onOpenChange={(o) => { if (!devolver.isPending) { if (o) devolver.reset(); setOpen(o); } }}`. (3) O resultado 'reapareceu' fica numa linha persistente (estado próprio, não o `anunciar` de 2,2 s) ou só no histórico; o 'recriado' pode usar `anunciar`. (4) `onError` com `codigo` de estado invalida `['event', id]` e a faixa. (5) No `onSuccess`, ler `updated.devolucao_google?.resultado` só ali; nenhum componente lê a chave do cache depois.

**Evidência da revisão.** frontend/packages/ui/src/components/confirm-dialog.tsx:14, :48, :60-62; frontend/packages/ui/src/index.ts:38; frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:217-220, :228, :330-331, :340, :408-412; app/api/agenda_read.py:189; frontend/packages/api-client/src/queryClient.ts:31-41; specs/303-sync-nao-apaga-venda/spec.md:35-37

## DG-10 — (d) Qual é o texto de orientação do caso 'recriado à mão com id novo' e onde ele aparece?

**Decisão.** Texto fixo, dentro da faixa da marca, só para quem tem flags.can_delete, recolhido atrás de um título clicável ('O evento já foi recriado à mão no Google?') para não competir com os dois botões. Não há detecção automática do evento duplicado nem link para ele.

**Porquê.** A spec manda a tela dizer isso ao Superadmin (Casos de borda, 'Recriado à mão') e põe a fusão automática fora de escopo; detectar o 'provável duplicado' por data ou título seria meio caminho de uma fusão e uma consulta a mais em toda abertura de evento marcado. O texto precisa impedir o erro específico do caso 1244: cancelar o antigo, que é o que tem os comprovantes. Recolhido porque a maioria dos eventos marcados não foi recriada.

**Alternativas rejeitadas.** (1) Texto sempre aberto — rejeitado: quatro frases acima dos botões em toda tela de evento marcado. (2) Procurar e listar eventos criados depois da marca na mesma data — rejeitado: fora de escopo e sujeito a falso positivo. (3) Pôr o texto no diálogo de cancelamento — rejeitado: chega tarde; a pessoa já escolheu cancelar. Pode haver lá uma linha curta remetendo a ele, mas isso é da frente do cancelamento.

**Contrato.** Título: 'O evento já foi recriado à mão no Google?'
Corpo: 'Se alguém recriou este evento no Google Agenda, existe agora um segundo evento no sistema, sem os dados deste. Não cancele este: é ele que guarda os comprovantes, o contrato e a escala. Devolva este ao Google Agenda e apague o outro lá no Google — se estiver vazio, o sistema o remove sozinho na próxima sincronização. Cancelar este aqui geraria comissão em dobro, e a cobrança do evento novo pediria de novo o que a cliente já pagou. Se o evento recriado já tiver venda lançada, ele também fica marcado quando sair do Google: cancele-o escolhendo "Nada" a devolver.'

**Pontos de toque.**
- frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:378-406 (faixa; bloco novo dentro da faixa da marca)
- frontend/packages/ui (AccordionRow já exportado — reuso para o recolhido, se a faixa não usar <details>)
- docs/02_MAPA_DE_PAGINAS_E_UX.md (tela do evento: marca e saídas)

**Riscos.**
- O Superadmin ainda precisa achar e apagar o evento duplicado no Google por conta própria; enquanto não apagar, a agenda mostra os dois.
- Depois de devolver o antigo, o Google tem dois eventos na mesma data até o novo ser apagado.

**Verify.** Sem cenário de API (texto estático). Conferência de tela: visível para Superadmin, ausente para Comercial; abre e fecha; sem rolagem horizontal na largura de celular da tela interna. Varredura de prosa da FR-025 deve normalizar quebras de linha antes de casar frases (o texto atravessa linhas de ~100 colunas).

**Revisão adversarial: parcial.** Conteúdo alinhado ao caso de borda 'Recriado à mão' e à exclusão da fusão automática. O texto, porém, induz dois erros: (1) Ordem: 'Devolva este e apague o outro lá no Google'. Depois de devolver, o Google tem dois eventos de mesmo título, às vezes no mesmo dia; apagar o errado (o recém-devolvido) marca o evento de novo. (2) Não diz que a devolução usa a data que está no sistema. No 1244 o evento antigo está na data velha; devolver sem acertar a data recria o evento no dia errado e deixa o recriado à mão, na data certa, para ser apagado. Menores: 'o sistema o remove sozinho na próxima sincronização' só vale para mês dentro do horizonte do ciclo automático (mês passado só sai pelo 'Limpar eventos fantasma'); e 'AccordionRow, se a faixa não usar <details>' deixa aberta uma escolha que o Princípio XI fecha (expansão com transição).

**Emenda.** Reescrever o corpo em passos numerados: '1. Acerte neste evento a data, o horário e o local que valem agora — a devolução usa o que está no sistema. 2. Abra o evento recriado pelo sistema, entre em Editar no Google Agenda e apague-o lá (se estiver vazio, o sistema o remove na sincronização seguinte; se já tiver venda, ele fica marcado — cancele-o escolhendo "Nada"). 3. Só então devolva este ao Google Agenda. Não cancele este: é ele que guarda os comprovantes, o contrato e a escala; cancelar geraria comissão em dobro e a cobrança do evento novo pediria de novo o que a cliente já pagou.' Fixar `AccordionRow` do @manto/ui, não `<details>`. A varredura de prosa da FR-025 normaliza as quebras de linha antes de casar.

**Evidência da revisão.** specs/303-sync-nao-apaga-venda/spec.md:35-37, :373-378, :789-794; app/calendar/sync.py:51-70 (o ciclo começa no mês corrente); frontend/packages/ui/src/index.ts:41; .specify/memory/constitution.md:192-198; frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:243-248

## DG-11 — (e) O que acontece com os ensaios-filho do evento devolvido?

**Decisão.** A devolução não toca em ensaio nenhum. O evento devolvido é a MESMA linha (mesmo id), então os ensaios que continuam no banco seguem ligados a ele por parent_event_id, com o próprio evento no Google intacto. Ensaio que também foi apagado do Google já terá sido removido pelo sync como evento vazio (caso de borda da spec: 'o pai marcado não arrasta o ensaio') e não é recriado: não existe mais registro de onde recriar. O evento devolvido continua com needs_rehearsal como estava, e a equipe de ensaio reagenda pelo painel de ensaio. O diálogo de confirmação avisa disso em uma frase (DG-9). O núcleo serve igual para um ENSAIO que eventualmente esteja marcado: os cinco campos são os mesmos e parent_event_id não é tocado.

**Porquê.** Ensaio é um CalendarEvent próprio, com google_event_id próprio (event_ops.py:1642-1654), ligado por parent_event_id, que o sync nunca sobrescreve (routes.py:2306). Trocar o google_event_id do pai não afeta o filho. Recriar ensaios apagados exigiria guardar dados de ensaio que o sync já apagou — é outra feature. O título do ensaio no Google ('🟧 ENSAIO — <título do pai>') pode ficar defasado se o pai foi renomeado enquanto marcado, mas isso já acontece hoje em qualquer renomeação.

**Alternativas rejeitadas.** (1) Recriar no Google os ensaios do pai junto com ele — rejeitado: os que sumiram não existem mais no banco, e os que existem não sumiram. (2) Marcar também os ensaios quando o pai é marcado, para devolvê-los juntos — rejeitado: contradiz o caso de borda decidido na spec. (3) Aviso automático na resposta quando needs_rehearsal é verdadeiro e não há ensaio — rejeitado: a tela do evento já mostra o estado do ensaio; seria um segundo aviso do mesmo fato.

**Contrato.** Nenhum campo, nenhuma chamada: devolver_ao_google não lê nem escreve event.ensaios. Invariante: depois da devolução, todo CalendarEvent com parent_event_id = <id do evento> continua com o mesmo parent_event_id e o mesmo google_event_id.

**Pontos de toque.**
- app/models.py:298, 352-357 (parent_event_id e relação ensaios com cascade)
- app/calendar/event_ops.py:1619-1655 (create_ensaio: evento próprio no Google)
- app/calendar/routes.py:2306 (sync não sobrescreve parent_event_id), :2355-2359 (sync apaga roles de ensaio)
- app/api/agenda_read.py:762-777 (payload: ensaio_pai e ensaios)
- app/calendar/event_ops.py:505-538 e o _sair_de_show (troca de tipo saindo de SHOW apaga ensaio do Google de verdade — continua valendo enquanto marcado; é da frente da FR-008)

**Riscos.**
- Pai SHOW devolvido sem ensaio (o ensaio sumiu junto) volta a constar como 'precisa de ensaio' sem ensaio agendado — é o estado correto, mas depende de a equipe de ensaio notar.
- Enquanto o pai está marcado, trocar o tipo saindo de SHOW ainda apaga os ensaios do Google para valer; a devolução recria só o pai, já sem ser SHOW.
- Quando o pai marcado é um evento VAZIO e o sync o apaga, os ensaios caem em cascata sem _clear_event_side_tables e o EventLog do ensaio estoura FK (risco 8 da síntese) — é da frente do sync, mas aparece nos mesmos dados de teste.

**Verify.** Cenário 10h: o evento do cenário 10 tem um ensaio-filho descartável (linha com parent_event_id = id do evento e google_event_id próprio com o prefixo do verify). Depois da devolução, por conexão separada: o ensaio existe, com o mesmo parent_event_id e o mesmo google_event_id; o dublê de insert recebeu 1 chamada (a do pai), nenhuma com título começando por '🟧 ENSAIO'; dublês de update e delete com 0 chamadas.

**Revisão adversarial: sim.** Sustenta. O ensaio é um `CalendarEvent` próprio, com `google_event_id` próprio e `parent_event_id` que o sync nunca sobrescreve; a devolução troca o id do pai na MESMA linha, então os filhos continuam ligados. Não recriar ensaio apagado está de acordo com o caso de borda 'o pai marcado não arrasta o ensaio'. Única ressalva: a frase 'o núcleo serve igual para um ENSAIO marcado' não tem cenário, e na prática ensaio não é marcado (o sync apaga as vagas dele a cada rodada e ele não tem venda).

**Emenda.** Retirar a afirmação sobre ensaio marcado ou cobri-la com uma recusa explícita; não deixar caminho sem verify. Manter o cenário 10h como está. O aviso 'ensaios apagados não voltam' fica no diálogo (DG-9).

**Evidência da revisão.** app/calendar/event_ops.py:1564, :1639-1654; app/calendar/routes.py:2306, :2355-2359; app/models.py:298, :352-357; app/api/agenda_read.py:762-778; specs/303-sync-nao-apaga-venda/spec.md:400-401

## O que a frente deixou de decidir (revisão)

- Data que vai ao Google: nenhuma decisão trata o evento marcado cuja data no sistema está velha ou já passou (o caso 1244: 19/09 no sistema, recriado à mão para 07/11). A spec diz que devolver 'vale mesmo no passado', mas a tela precisa mostrar título e data que serão enviados e orientar a editar antes (specs/303-sync-nao-apaga-venda/spec.md:35-37, :388-389). Emendas em DG-9 e DG-10.
- Semântica do ramo 'reapareceu' quando o evento foi editado enquanto marcado: a FR-012 diz 'dados atuais' e a síntese decidiu 'vale o Google' só para o ciclo automático. Falta decisão registrada para o clique do Superadmin (specs/303-sync-nao-apaga-venda/spec.md:472-474).
- Convenção de carimbo: o plan precisa fixar, para o EventLog e para a coluna da marca, se o horário é UTC sem fuso (default do modelo, que `_serialize_logs` assume) ou horário de São Paulo sem fuso (como `cancelled_at`). A mensagem 'marcado desde dd/mm/aaaa' e o histórico dependem disso, e o cancel_ops hoje grava o EventLog 3 h adiantado (app/api/agenda_read.py:210-214; app/calendar/cancel_ops.py:272, :299-305).
- Falha ambígua do insert: o Google criou e a resposta se perdeu. Não há timeout explícito em `build()` (app/calendar/service.py:241), e o risco, a mensagem e o teto real do bloqueio da linha (mais de 60 s, não '~1 s') não foram decididos.
- Interface com a frente do cancelamento: o botão 'Cancelar e devolver o dinheiro' abre o ExcluirEventoDialog, que decide pela `acao` de `pode_excluir`. Um marcado que só tem grupo (satélite sem venda, comprovante, contrato ou escalado próprios) cai em 'excluir', e o DELETE tenta apagar do Google um evento que não está lá, contra a FR-013 e contra a preservação do satélite (app/calendar/cancel_ops.py:57-74; app/api/agenda_write.py:519-538). O rótulo e o destino do botão para evento marcado precisam ser fechados entre as duas frentes.
- Contrato entre frentes ainda sem nome: o módulo e a assinatura da consulta de três estados, o helper único de desmarcar (com `actor` opcional), a coluna da marca, e o `kind` e `entity_type` do sino. O plan deve fixá-los num lugar só (data-model e contracts) e ordenar as tasks: consulta e marca antes do núcleo da devolução. Os cenários 10c e 10e dependem deles.
- Tamanho das funções: '1 função de ~120 linhas' precisa virar orquestradora mais helpers de até ~30 linhas (.specify/memory/constitution.md:43-44).
- Token do Google revogado ou desconectado: hoje cairia em 'inconclusivo — tente de novo em instantes'. Falta um código e uma mensagem que apontem para /google/connect (app/calendar/routes.py:4045-4047).
- Documentação das travas além do que a proposta lista: CLAUDE.md:98, .claude/skills/manto-verify/SKILL.md:23, DEVELOPMENT.md:105 e docs/01_SISTEMA_E_BANCO.md:1866 afirmam que as travas cobrem só e-mail e convite.
- Caminho feliz nunca exercitado contra o Google real antes da produção (a trava impede localmente): o quickstart do plan deveria prever um teste pós-deploy com um evento descartável — marcar, devolver, conferir o id novo e a ausência de duplicata no ciclo seguinte — em vez de deixar o primeiro uso real ser o teste.

## Perguntas em aberto da frente
