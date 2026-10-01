# Frente verify

Verify (verify_303.py) e ordem de construção — feature 303 / 303b

Tamanho: Grande. 303: verify_303.py com ~2.000 a 2.300 linhas (36 cenários mais sub-cenários, dublê do Google de ~150 linhas), dre_dump.py ~150, contagem_pre_deploy.py ~200, ajuste de 2 linhas no verify_205; 1 migration, 11 fases de construção em 2 marcos. 303b: verify_303b.py ~400 linhas (4 cenários mais limpeza), sem migration.

## V1 — (a) Como substituir o Google (lista do mês, consulta de um evento, criação, atualização, remoção) sem tocar a agenda real, inclusive nas chamadas feitas dentro de requisições HTTP do test_client?

**Decisão.** Um dublê único, `GoogleFalso`, instalado no topo do verify nos DOIS nomes que toda função de `app/calendar/service.py` resolve em tempo de chamada: `service.build` (cliente da API) e `service.load_credentials`. Não se troca função por função. O dublê é fail-closed: mês não liberado faz `events.list` levantar HttpError 503; id desconhecido faz `events.get` levantar HttpError 503 (inconclusivo). Erros são os tipos reais (`googleapiclient.errors.HttpError` com `resp.status` 404/410/500/503, `TimeoutError`, `google.auth.exceptions.RefreshError`). Toda chamada fica registrada para asserção. Junto: dublês de Maps/ViaCEP (`routes._lookup_sp_status`, `routes._fetch_travel_data`, `maps.cidade_do_endereco`), de e-mail (`email_service._send` captura) e de `formularios_ops.retry_auto_link_pending`; e um disjuntor de rede (`socket.socket.connect` recusa host que não seja loopback e anota a tentativa), cuja lista vazia é asserção do último cenário. A trava nova da FR-024 é conferida ligada logo depois do `create_app()` e desligada por `app.config[...]` só nos cenários que precisam escrever no dublê.

**Porquê.** `routes.py` importa cinco funções do service no topo (routes.py:19-29) e os outros consumidores importam tarde (sync.py:49; admin_config_write.py:61; cancel_ops.py:280; event_ops.py:548, 1635, 1669, 1699; virtuais_ops.py:1152, 1665). Trocar `service.insert_event` não alcança `routes.insert_event`: a 302 precisou trocar os dois (verify_302.py:102-105) e a 299, três módulos (verify_299.py:109-114). Mas todas chamam `load_credentials()` e `build("calendar","v3",...)` pelo global do módulo service (service.py:135-139, 183-186, 238-241, 276-279, 364-367), então trocar esses dois nomes cobre tudo, inclusive a função de consulta tri-estado e a paginação que o núcleo ainda vai criar — o verify é escrito antes do núcleo e não pode depender do nome delas. O test_client roda no mesmo processo, logo a requisição HTTP usa os mesmos módulos. `load_credentials` também é trocado porque o real renova o token pela rede e grava (`save_token`, service.py:128-130, 60-90). Fail-closed é obrigatório: `run_calendar_sync` varre do mês corrente até o último evento do banco +1 (sync.py:51-70) e o `cleanup_past` varre todo mês com evento (admin_config_write.py:92-106); um dublê que devolvesse lista vazia para mês real faria a limpeza apagar (hoje) ou marcar (depois) os eventos reais do espelho. Com a exceção, o mês cai no `except` e a limpeza não roda (sync.py:83-85; admin_config_write.py:107-108).

**Alternativas rejeitadas.** (1) Trocar as funções do service uma a uma (molde 205/299/302): rejeitada — dois bindings por função, não cobre função nova, e esse molde já deixou `_cleanup_stale_events([])` rodar sobre um mês real do espelho (verify_205.py:809-810). (2) Usar a trava da FR-024 no lugar do dublê: rejeitada — trava cala escrita, não responde leitura, e o cenário 10 precisa provar a criação. (3) `HttpMockSequence` do googleapiclient: rejeitada — sequência posicional quebra a cada mudança na ordem de chamadas do núcleo.

**Contrato.** class GoogleFalso (dentro do verify_303.py):
  itens: dict[str, dict]  # id -> item vivo (summary, description, location, start/end.dateTime, htmlLink; SEM `created`)
  apagados: dict[str, str]  # id -> '404' | '410' | 'cancelled'
  falhas: dict[str, Exception]  # id -> exceção no get
  meses_liberados: set[tuple[int, int]]
  credencial: 'ok' | 'ausente' | 'refresh_falha'
  lista_fora: bool; pagina: int | None  # None = lista inteira; n = devolve n itens + nextPageToken
  chamadas: list[tuple[str, dict]]  # ('list'|'get'|'insert'|'patch'|'delete', kwargs)
  registrar(item) / apagar(id, como='404') / mover(id, inicio, fim) / restaurar(id)
  build(api, version, credentials=None, **kw) -> serviço com events().list/get/insert/patch/delete/list_next, cada um com .execute()
  load_credentials() -> object | None (ou levanta RefreshError)
Regras: list em mês não liberado -> HttpError 503; get de id vivo -> item; apagado 'cancelled' -> {'id','status':'cancelled'} sem título nem início; '404'/'410' -> HttpError; id desconhecido -> HttpError 503; insert -> id 'v303g-N' + htmlLink falso; patch/delete em apagado -> HttpError 404.
Instalação: cal_service.build = google.build; cal_service.load_credentials = google.load_credentials; cal_routes._lookup_sp_status = lambda loc: False; cal_routes._fetch_travel_data = lambda ev, s: {}; maps.cidade_do_endereco = lambda e: (None, None); es._send = captura; formularios_ops.retry_auto_link_pending = lambda: 0.
Disjuntor: socket.socket.connect embrulhado; host fora de {127.0.0.1, ::1, localhost} -> RuntimeError e append em `rede_bloqueada`.

**Pontos de toque.**
- app/calendar/service.py:10 (import de build), :93-132 (load_credentials; refresh em 128-130), :134-158 (lista sem paginação, maxResults em 155), :181-191 (consulta engole qualquer erro como None), :217-263, :266-288, :362-368
- app/calendar/routes.py:19-29 (bindings congelados), :2197-2208 (guarda de 5 min por `created`), :2279, :2328 (_lookup_sp_status), :2283, :2332-2335 (_fetch_travel_data), :4191-4208 (Sincronizar de um evento)
- app/calendar/sync.py:43-49, :51-70, :74-85, :87-94 (retry_auto_link_pending)
- app/api/admin_config_write.py:48-119
- app/api/agenda_write.py:541-566 (cancelar), :621-636 (sync do evento)
- app/calendar/cancel_ops.py:278-286 (delete no Google dentro do cancelar)
- app/config.py:100-118, :121-142 (travas existentes; a de evento de show não existe)
- app/email_service.py:964-987
- specs/302-portal-detalhes-do-evento/verify_302.py:99-117; specs/299-sem-valor-cobrancas/verify_299.py:87-114; specs/205-loja-interacoes-virtuais/verify_205.py:1296-1317 (HttpError real)

**Riscos.**
- Se o núcleo criar cliente Google fora de service.py, o dublê não pega; o disjuntor de rede pega e o cenário final falha — por isso o disjuntor não é opcional.
- Item do dublê com `created` recente e sem linha local é pulado por `sync_events` (routes.py:2197-2208): os itens nascem sem `created`, senão o cenário 8 passa a vazio.
- Exceção do disjuntor engolida por `except Exception` do app (ex.: routes.py:2467) não derruba o cenário; só a asserção final sobre `rede_bloqueada` a revela.
- O formato real da resposta do Google para evento apagado (404, 410 ou status 'cancelled') é suposição até a sonda da decisão V8; o dublê modela os três.

**Verify.** Cenário 13 em quatro variantes (get com HttpError 500, TimeoutError, credencial ausente, RefreshError): nada apagado nem marcado. Lista incompleta (`pagina=1` com nextPageToken) não apaga evento vivo fora da página. Cenário 10: exatamente um `insert` com título, data, horário, local e descrição atuais; 10b (novo): com a trava ligada, zero `insert`, marca continua e a resposta diz por quê. Cenário 12: zero `delete` para o id do evento marcado. Cenário 14: zero `patch`, zero e-mail capturado, roles intactas. Os três caminhos que limpam são exercitados ao menos uma vez: `run_calendar_sync()`, `POST /api/admin/sync/run {action: cleanup_past}` e `GET /agenda?force_sync=1&ym=`. Primeira asserção do verify: `MAIL_SUPPRESS_SEND is True` e a trava nova `is True`.

**Revisão adversarial: parcial.** O núcleo da decisão se sustenta: todas as funções de service.py resolvem `load_credentials` e `build` pelo global do módulo, e nenhum outro ponto de app/calendar cria cliente do Google. Cinco furos no contrato:

1. **E-mail sai por thread.** `send_async` dispara `threading.Thread(daemon=True)`, e é por ele que saem o e-mail de evento alterado e o alerta de ensaio. A captura em `es._send` acontece depois, em outra thread. "Cenário 14: zero e-mail capturado" passa por corrida, e a thread que roda depois da limpeza recarrega o objeto por PK e acha None. `send_async` é importado por nome em três módulos, então trocá-lo cai no problema de vários bindings que V1 diz evitar.

2. **Cenário 13, variantes "credencial ausente" e "RefreshError", passam a vazio.** O estado `credencial` é global, então derruba o `events.list` antes: `fetch_events_for_month` levanta e o mês é pulado. Ficam verdes hoje e depois do núcleo sem nunca chegar à confirmação por id da FR-003.

3. **Dublê incompleto.** `list` precisa filtrar por `timeMin`/`timeMax` e aceitar `pageToken` além de `list_next` (o núcleo ainda não existe e pode paginar de um jeito ou de outro). Não há `reset` nem liberação de mês por bloco: `run_calendar_sync` e `cleanup_past` varrem todos os meses liberados de uma vez, e `falhas`/`credencial` vazam entre cenários.

4. **`/agenda?force_sync=1` só captura `RuntimeError`.** O `HttpError` 503 do mês não liberado propaga (com `TESTING=True` vira exceção no test_client). O contrato precisa dizer que esse caminho só é exercitado em mês liberado.

5. **A trava da FR-024.** "Desligada por `app.config[...]`" só funciona se o núcleo ler `current_app.config[<CHAVE>]` em tempo de chamada. Nome da chave e modo de leitura não estão em contrato nenhum, e o verify é escrito antes do núcleo.

**Emenda.** Manter os dois nomes trocados e o fail-closed. Acrescentar ao contrato:

- `_esperar_threads()`: `join(timeout)` em toda thread viva que não seja a principal. Chamar antes de qualquer asserção sobre `_emails` e antes da limpeza. Não troca binding nenhum.
- Credencial por chamada: `credencial` aceita sequência ou callable por índice de chamada de `load_credentials` (1ª = list, ok; seguintes = get, None ou RefreshError). Cada variante do 13 ganha controle positivo: o mesmo evento, com o get respondendo 404, é marcado. As variantes em que a lista inteira cai viram um sub-cenário separado, declarado "verde antes do núcleo".
- `GoogleFalso.list` honra `timeMin`, `timeMax` e `pageToken`. `with google.liberar(mes):` por bloco e `google.reset()` entre cenários.
- `contracts/` fixa o nome da chave da trava e "lida de `current_app.config` a cada chamada".
- O disjuntor embrulha também `connect_ex`.

**Evidência da revisão.** app/calendar/service.py:135-139, 162-166, 183-186, 238-241, 276-279, 324-327, 364-367 (globais do módulo); :148-156, :168-176 (parâmetros do list). app/email_service.py:25-63 (`send_async`, thread daemon em :63). app/calendar/event_ops.py:37, :75, :81; app/calendar/casting_ops.py:22; app/gastos/gastos_ops.py:27, :316. app/calendar/sync.py:77, :83-85. app/calendar/routes.py:470-479 (só `RuntimeError`), :2391 (`send_removal_email` síncrono). app/api/admin_config_write.py:99-108.

## V2 — (a) Como semear eventos, comprovantes, contrato, grupo, comissões em cada status, BV e devolução sem inventar EventRole com personagem, sem disparar e-mail e sem o sync destruir o espelho?

**Decisão.** Duas famílias de evento. (1) Eventos de SYNC (blocos H1, H2, H3, H5, H6): vivem em meses isolados (2031-03 em diante e um mês passado, 2016-02), onde o banco não tem evento real; nascem pelo caminho real — o item é registrado no dublê e importado por `sync_events([item])` —, então Coordenador, personagens do título e, em SHOW, as duas vagas de som são criados pelo sistema. 'Escalar' é pôr um talento DESCARTÁVEL na role que o sistema criou com `talent_id IS NULL`; nenhuma role é criada pelo verify. (2) Eventos de DINHEIRO (H4, H7): semeados direto (`source='platform'`, `google_event_id='v303-<nome>'`) em meses reais (M = mês corrente, E = dia 15 de M+2, e M-1 para a Tendência), registrados no dublê mas em mês não liberado; nunca passam pelo sync. Comprovante, contrato, grupo e BV são INSERT direto; comissão nasce pelo motor (`_sync_commission_payment`) com `commission_rate=5` gravado no evento e vendedor descartável; 'paga' e 'repasse liquidado' usam os endpoints reais da Planilha; devolução nasce SEMPRE por `POST /api/events/<id>/cancelar`. Um guarda aborta o verify (exit 2) se algum mês isolado tiver evento que não seja do verify.

**Porquê.** `_cleanup_stale_events` olha todo evento do mês (routes.py:352-368): rodar o sync num mês real com lista falsa mexe nos eventos reais do espelho. Data distante é a receita da skill (SKILL.md:72-73). Para evento que não é `platform`, o sync reconcilia as roles contra o título e apaga a que sobra, mandando e-mail de remoção antes (routes.py:2361-2392): role nascida do próprio título nunca sobra, e é o que a regra pede ('assuma role existente com talent_id IS NULL', DEVELOPMENT.md:230-233). A 302 já releu a regra: o proibido é pendurar cargo inventado em evento REAL (verify_302.py:28-34). O vendedor descartável (`receives_commission` é True por padrão, models.py:74) isola a linha da Planilha, que é agregada por vendedor e ciclo (financeiro/routes.py:928-961): dá para afirmar valor exato e 'repasse liquidado não reabre'. A taxa gravada no evento tira a dependência do padrão de 2,5% (comissoes_ops.py:576, 590-596). Devolução semeada à mão não provaria a FR-013.

**Alternativas rejeitadas.** (1) Assumir role de evento real com `talent_id IS NULL`: rejeitada — escreve talento de teste em linha de produção e depende da limpeza para desfazer (verify_302.py:28-34). (2) Semear evento de sync por INSERT com `source='platform'` (o sync preserva as roles, routes.py:2351-2353): rejeitada como padrão — os eventos que somem do Google em produção são importados, e a reconciliação pelo título é justamente o risco do 'Sincronizar' num marcado; fica só para os eventos de dinheiro. (3) Tudo em meses reais: rejeitada pelo motivo do primeiro parágrafo.

**Contrato.** Constantes: PREFIX='v303' (todo google_event_id começa assim); TITULO_TESTE='[TESTE verify 303] pode apagar' na descrição; MES_H1=(2031,3), MES_FALHA=(2031,4), MES_ORIGEM=(2031,6), MES_DESTINO=(2031,9), MES_PASSADO=(2016,2), MES_AVISO=(2031,11), MES_DECISAO=(2032,2), MES_PORTAL=(2032,4).
Helpers:
  _mes_vazio(ano, mes) -> None  # exit 2 se houver evento sem o prefixo
  _evento_google(nome, quando, *, tipo='R&I', personagens=('V303 BLUEY',), local, descricao) -> int  # registra no dublê + sync_events([item])
  _evento_direto(nome, quando, *, venda=None, vendedor=None, taxa=None, com_nota=False, lider=None, cancelado=False) -> int
  _escalar(event_id, talento_id, *, vaga=None) -> int  # preenche role existente com talent_id NULL; nunca cria
  _comprovante(event_id, valor); _contrato(event_id); _grupo(lider_id, satelite_id)
  _bv(event_id, valor, *, pago=False); _parcelas(event_id, [...]); _nota_a_emitir(event_id, valor)
  _comissao_pelo_motor(event_id) -> int  # _sync_commission_payment + commit
  _usuario(sufixo, papel, *, receives_commission=True) -> (email, id)  # SUPERADMIN, COMERCIAL (vendedor), FINANCEIRO, FIGURINO
  _talento(sufixo) -> Talent  # e-mail @manto.local
Exemplo da spec parametrizado por data relativa: cancelamento hoje (mês M), evento em M+2 dia 15; variante com evento em M-1 para a Tendência.

**Pontos de toque.**
- app/calendar/routes.py:352-368 (a limpeza olha o mês inteiro), :2060-2090 (vagas de som; talento 42 em :2073-2078), :2247-2283 (importação cria roles), :2351-2353, :2361-2392
- app/calendar/routes.py:1915-1932 (parse_event_type, parse_characters)
- app/models.py:74, :244 (google_event_id NOT NULL UNIQUE), :646-675 (EventContract, EventPayment), :1789-1816 (EventAcrescimo/BV)
- app/financeiro/comissoes_ops.py:590-596, :656-686, :804-876
- app/financeiro/routes.py:904-961 (item de comissão por vendedor e ciclo), :1020 (abrir a Planilha gera salários do mês visto)
- app/api/financeiro_write.py:54 (set-status), :329 (pagar-mes)
- specs/299-sem-valor-cobrancas/verify_299.py:188-248 (molde de evento, comprovante, comissão); specs/302-portal-detalhes-do-evento/verify_302.py:177-252 (talento e staff descartáveis)

**Riscos.**
- SHOW semeado ganha a vaga 'Técnico de Som' com o talento real 42 (routes.py:2073-2078): aparece no portal dele só no espelho, sem e-mail; a limpeza apaga a role junto com o evento. Cenário de data passada não usa SHOW.
- Abrir a Planilha de M+2 gera `SalaryPayment` daquele mês no espelho (financeiro/routes.py:1020): efeito conhecido, igual ao de qualquer pessoa abrindo a tela; fica documentado no cabeçalho do verify.
- O cenário 'avaliação de evento cancelado' precisa de evento que terminou nos últimos 7 dias, em mês real: semeado direto, nunca sincronizado.
- Se um refresh do espelho trouxer evento real para um mês isolado, o verify aborta em vez de rodar — é o comportamento desejado.

**Verify.** Cenário 5 usa a role de personagem que o sync criou do título; 7 usa SHOW só com as vagas automáticas (apagado); 7a, a vaga de Presença designada e a vaga 'Técnico de Som' com o talento descartável no lugar do 42 (ficam). Sub-cenário de 7: pai vazio com ensaio-filho que tem EventLog (o risco de FK de models.py:352-357). Cenário 2: a contagem esperada de notificações vem de `resolver_destinatarios((COMERCIAL, SUPERADMIN))` (notificacoes_ops.py:82-98), lida antes do sync. Cenário 20: o vendedor tem um repasse liquidado (ciclo M-1, pago pela Planilha) e uma segunda venda a pagar no ciclo M; o desconto de -80 é localizado por SQL (`seller_id` do descartável, `amount < 0`), seu ciclo tem de cair num item não liquidado e o item liquidado continua 'pago' com o mesmo total.

**Revisão adversarial: parcial.** A parte do sync se sustenta: a reconciliação só mexe em role que não é `extra` e que não está no título, a vaga de som nasce com o talento 42, e evento criado agora com `sale_date` em M−1 fica no ciclo M−1 (a regra da 299 exige cadastro em mês anterior). Quatro lacunas:

1. **Abrir a Planilha escreve mais do que V2 diz.** Ela gera `SalaryPayment` e também `RecurringExpenseEntry` do mês visto, na API e no Jinja. A DRE lê os dois: `pessoal` troca de pro-rata (salário ÷ 30 × dias, arredondado a 1) para a soma real, e `gastos_recorrentes` sai de zero. V2 lista só o salário, como "efeito conhecido", e não liga isso às medições de V4.

2. **Backend local ligado durante o verify.** Em dev a thread de sync sobe quando `WERKZEUG_RUN_MAIN=true`. Com eventos de teste em 2032 o horizonte estica até lá (cerca de 69 `list` reais por ciclo). Os eventos de dinheiro em meses reais, com id `v303-`, não estão no Google real: são apagados (código de hoje) ou marcados com sino para usuários reais do espelho (depois do núcleo), no meio da execução. Não há guarda.

3. **EducaManto.** O beneficiário de evento "(EDU…" é o responsável real configurado. A linha de comissão nasce em usuário real e a limpeza por `seller_id` descartável não a encontra (o cancelamento ainda zera o `event_id`). A FR-016/018 pede EducaManto e o desenho não diz se há variante EDU.

4. **`MES_PASSADO=(2016,2)` é constante.** Se o espelho tiver evento lá, o verify aborta sempre.

**Emenda.** - Bloco B0 ganha um aquecimento: `GET /api/financeiro/pagamentos?month=` para M−1, M, M+1 e M+2, antes de qualquer medição de DRE. O cabeçalho do verify declara os dois efeitos (salários e recorrentes).
- Guarda de ambiente (exit 2): `site_settings.calendar_auto_sync_at` com menos de 15 minutos significa processo com thread neste banco; a mensagem manda parar o backend local.
- Variante EDU: ou o plano declara que nenhum fixture usa título "(EDU" e a regra EducaManto é provada pelo cálculo (comissão cheia gravada à mão), ou o verify troca `settings.educamanto_seller_id` por um descartável dentro do cenário e restaura no finally. Em qualquer caso a limpeza de `commission_payments` filtra por `seller_id` descartável OU `event_title LIKE '%v303%'`.
- `MES_PASSADO` calculado: o mês anterior ao evento mais antigo do espelho.
- Satélite entra na limpeza antes do líder.

**Evidência da revisão.** app/api/financeiro_read.py:680, :722; app/financeiro/routes.py:1020, :1062, :717-762 (`_ensure_salary_payments`); app/gastos/gastos_ops.py:498-543. app/financeiro/routes.py:181-202 (`_salary_cost`), :306-313; app/api/financeiro_read.py:242, :253-260. app/__init__.py:240-269 (thread em dev); app/calendar/sync.py:56-64. app/financeiro/comissoes_ops.py:643-653 (beneficiário EDU), :689-710 (`_valor_chegou_depois`). app/calendar/cancel_ops.py:139-155. app/calendar/routes.py:2060-2090, :2361-2404. app/models.py:305, :365-370.

## V3 — (a) Qual é o esqueleto do verify_303.py: conferência de escrita, colunas que ainda não existem, limpeza no finally?

**Decisão.** Arquivo único `specs/303-sync-nao-apaga-venda/verify_303.py` no molde 299/302, com quatro regras próprias. (1) O verify não importa NADA que a 303 cria: coluna nova é lida por SQL cru na conexão separada, e as rotas novas ficam num dicionário `ROTAS` no topo, copiado de `contracts/`. (2) Três estados por cenário: OK, FALHA e BLOQUEADO (depende de outra história que ainda não existe); qualquer FALHA ou BLOQUEADO devolve exit 1; problema de ambiente devolve exit 2. (3) Todo cenário 'deve falhar' tem controle positivo no mesmo cenário: o Superadmin recebe 200 na mesma rota e o papel sem permissão recebe exatamente 403. (4) A limpeza roda antes (restos de execução quebrada) e no `finally`, e restaura o que o verify mexeu de global (`site_settings.calendar_sync_cache`).

**Porquê.** O autoflush esconde falta de commit (hotfix 257; SKILL.md:33-35), e o ORM com coluna que a migration ainda não criou estoura com erro de atributo, que é falha do harness e não da feature. Sem controle positivo, 'COMERCIAL tenta devolver ao Google' passa hoje com 404 de rota inexistente — o mesmo defeito que a 302 tratou com `_bloco_existe` (verify_302.py:363-376). `_mark_month_synced` guarda só 24 meses e descarta os mais antigos (routes.py:153-163): sincronizar meses de 2016 e 2031 expulsa meses reais do cache. As notificações de usuários reais sobre eventos de teste não caem com o usuário descartável (o CASCADE de models.py:633 só cobre as dele). `run_calendar_sync` grava um AuditLog por ciclo (sync.py:103-115).

**Alternativas rejeitadas.** (1) Conferir pelo ORM do app: rejeitada (autoflush; e coluna nova quebraria o import antes do núcleo). (2) Só dois estados (OK/FALHA): rejeitada — sem H1, todos os cenários que precisam de evento marcado falhariam com mensagem de sintoma, e o critério 'falha pelos motivos certos' (constituição VIII, constitution.md:155-159) se perde. (3) Apagar os eventos de teste com `_delete_event`: rejeitada — ele gera estorno de comissão (routes.py:325-327) e mistura a limpeza com o código sob teste.

**Contrato.** CLI: `verify_303.py [--bloco B1,B5] [--ate B3] [--rapido]`; sem argumento roda tudo (é o portão).
_no_banco(sql, **p) / _no_banco_todas(sql, **p)  # create_engine(DATABASE_URL) separado
_coluna_existe(tabela, coluna) -> bool  # information_schema; mensagem 'migration da 303 não aplicada'
cenario(nome, fn, *, bloco)  # OK | FALHA | BLOQUEADO; class Bloqueado(Exception)
_precisa_marcado(event_id)  # levanta Bloqueado('depende de H1') se o sync não marcou
D(valor) -> Decimal  # dinheiro do JSON em Decimal 0.01
ROTAS = {'faixa': ..., 'devolver_google': ..., 'alterar_devolucao': ...}
Saída: uma linha por cenário, resumo por bloco ('H1 7/9 · H2 0/2 bloqueado por H1'), total 'N/N OK'.
Limpeza, nesta ordem: rollback; notifications por entity_id dos eventos de teste e pelo kind novo; commission_payments por seller_id dos vendedores descartáveis (pega estornos sem event_id); special_expenses por event_id e por created_by descartável; _clear_event_side_tables(id) e db.session.delete(ev) por evento (filhos antes do pai); audit_logs (entity_id de teste; actor_name='auto-sync' desde o início do verify); clientes e talentos descartáveis; user.roles.clear() e delete do usuário; restaurar calendar_sync_cache; apagar a árvore temporária da main (V4).

**Pontos de toque.**
- DEVELOPMENT.md:202-233; .claude/skills/manto-verify/SKILL.md:22-25, :33-52, :54-64
- specs/302-portal-detalhes-do-evento/verify_302.py:120-135 (runner), :339-357 (limpar), :704-735 (main)
- specs/299-sem-valor-cobrancas/verify_299.py:85 (limiter pelo objeto), :118-130 (duas leituras por fora), :150-153 (D())
- app/calendar/routes.py:153-163 (_mark_month_synced), :259-302 (tabelas sem cascade), :393-414 (_log_sync)
- app/calendar/sync.py:103-115 (AuditLog do ciclo)
- app/models.py:328-364 (cascades do evento), :603-643 (Notification; CASCADE só por user_id em :633)
- app/calendar/cancel_ops.py:139-155 (estorno fica com event_id nulo — achável só pelo vendedor)

**Riscos.**
- Arquivo de ~2.000 linhas: grande, mas com precedente (verify_205 tem 1.621) e com blocos independentes.
- `--bloco` permite rodar menos do que o portão exige; o tasks.md precisa dizer que o portão é a execução sem argumentos.
- Limpeza que falha no meio deixa resto no espelho; por isso roda também no início e acha tudo pelo prefixo e pelos usuários descartáveis.

**Verify.** Login só por `POST /api/auth/login` (e `/api/portal/auth/login` para talento); requisições fora de `app.app_context()`; o sync (`run_calendar_sync`, `_cleanup_stale_events`) roda dentro de um contexto curto. Os cenários 11, 23b e 39 usam COMERCIAL e FINANCEIRO reais (o gate ignora o 'Ver como', agenda_write.py:83-94). Cenário 41 afirma zero resto: eventos, talentos, usuários, notificações, comissões, gastos, audit_logs do verify e `rede_bloqueada == []`.

**Revisão adversarial: parcial.** O esqueleto (conexão separada, três estados, controle positivo, limpeza antes e no finally, restauro do `calendar_sync_cache`) se sustenta. Problemas:

1. **Limpeza por `entity_id` sem `entity_type` apaga dado real.** Em `notifications` a referência é fraca: o mesmo inteiro pode ser uma resposta de formulário ou uma avaliação. "Pelo kind novo" sozinho apaga avisos reais do espelho depois que a 303 estiver em produção e o espelho for atualizado. O mesmo vale para `audit_logs`: `pay_seller_month` audita com `entity_id = seller_id`.

2. **O cenário 41 ("zero resto") não é verdade.** `SalaryPayment` e `RecurringExpenseEntry` gerados ao abrir a Planilha ficam no espelho.

3. **Contradição com V5.** V3 lê a coluna nova por SQL cru (`_precisa_marcado`), e V5 rejeita uma alternativa porque "o verify passaria a conhecer o nome da coluna". O verify conhece o nome de qualquer jeito.

4. **Falta o helper de contexto Jinja dentro do próprio verify.** Os cenários 23 e 35 pedem Planilha e Comissões "na tela antiga". O desenho só prevê a captura por `template_rendered` no `dre_dump.py`.

5. **Saída da primeira execução vermelha.** O precedente da casa é um arquivo na pasta da spec, não colar no tasks.md.

**Emenda.** - `notifications`: `DELETE ... WHERE kind = <novo> AND entity_id IN (ids de teste)`, mais `link_path LIKE` o caminho dos eventos de teste. Nunca por `entity_id` solto nem por kind solto.
- `audit_logs`: `entity_type='agenda' AND entity_id IN (ids)`, OU `detail LIKE 'gcal:v303%'` (pega o `auto_deleted` de evento já apagado), OU `entity_type='commission_month' AND entity_id IN (vendedores descartáveis)`, OU `actor_name='auto-sync' AND created_at >= início`.
- Cenário 41 passa a afirmar "zero resto, exceto salários e recorrentes dos meses M−1..M+2", listados.
- O nome da coluna da marca vem do `data-model.md`, numa constante no topo junto de `ROTAS`.
- `_contexto_jinja(client, url) -> dict` no verify, reusado pelo `dre_dump.py`.
- Primeira execução gravada em `specs/303-sync-nao-apaga-venda/verify_303_primeira_falha.txt`.

**Evidência da revisão.** app/models.py:596-600 (AuditLog), :609-610, :629, :639-640 (Notification sem FK). app/financeiro/comissoes_ops.py:540-548 (audit com `seller_id`). app/calendar/routes.py:153-163, :259-302, :393-414 (`gcal:<id>` no detalhe). app/notificacoes/notificacoes_ops.py:157-176. specs/299-sem-valor-cobrancas/verify_299_primeira_falha.txt (precedente). app/financeiro/routes.py:1006-1010, :1078 (Planilha Jinja viva).

## V4 — (b) Como fazer a prova por mutação do cenário 26 e a comparação main × branch do cenário 36 sem trocar de branch?

**Decisão.** Não usar snapshot guardado. Um script auxiliar, `specs/303-sync-nao-apaga-venda/dre_dump.py`, roda em subprocesso DUAS vezes por medição, uma por árvore de código, contra o mesmo `manto_local` e com segundos de diferença: `--raiz <repo>` (branch) e `--raiz <temp>` (main). A árvore da main é extraída na hora por `git archive --format=zip <BASELINE_SHA> app` (193 arquivos, 6,7 MB) numa pasta temporária; nada muda no repositório. `BASELINE_SHA` é constante fixada no verify (hoje `14cec75`, o merge-base), com guarda de que é ancestral de HEAD e diferente dela. O dump lê a DRE da API e o contexto da DRE Jinja (sinal `flask.template_rendered`, sem ler HTML), normaliza tudo em Decimal 0.01 e devolve JSON. Cenário 36 = bloco 0, antes de qualquer semeadura: todos os meses do espelho, as duas árvores, igualdade ao centavo. Cenário 26 = três estados medidos nas duas árvores — S0 (antes de semear o exemplo), S1 (semeado), S2 (cancelado): na branch S2−S0 do mês do cancelamento dá +400 / +40 / +18 / 0 / +342 e no mês do evento dá zero; na main, o MESMO banco dá gastos extras +600 e resultado −600.

**Porquê.** A DRE depende do relógio e escreve ao ser lida: a fronteira Realizado × Projetado é `start_at < agora` (financeiro_read.py:239-240; financeiro/routes.py:289-290), a Tendência é ancorada em hoje (financeiro_read.py:365-385) e `ensure_recurring_entries` roda em todo GET (financeiro_read.py:252; routes.py:305). Um snapshot tirado dias antes diverge sozinho, e um refresh do espelho — que a contagem pré-deploy (V8) exige — o invalida. Rodar as duas árvores no mesmo instante elimina as duas causas. A constante fixada mantém o cenário com sentido depois do merge (um merge-base dinâmico viraria branch × branch). É caixa-preta: não depende de nome de função do núcleo, então pode ser escrito antes dele. O mesmo mecanismo serve à prova por mutação: a main lendo o banco que a branch escreveu mostra o −600, o que prova que o cenário reproduz o defeito e que o comparador distingue as árvores. Precedente: a 263b roda a versão da main por `git show main:...` (verify_263b.py:398-407). A migration aditiva deixa o código da main ler o banco migrado.

**Alternativas rejeitadas.** (1) Snapshot JSON gerado antes do núcleo e versionado: rejeitada — envelhece com o relógio, morre no refresh do espelho e poria faturamento real da empresa no git. (2) `git stash` / checkout da main: rejeitada — mexe na árvore de trabalho, que tem muito arquivo vivo não versionado (CLAUDE.md §7). (3) `git worktree add`: rejeitada — deixa metadado em `.git/worktrees` e pede limpeza; o `archive` não toca o repositório. (4) Mutação em processo (monkeypatch devolvendo a regra antiga): rejeitada — exige conhecer os nomes do núcleo, e o verify vem antes.

**Contrato.** dre_dump.py --raiz <dir> --meses 2026-03,2026-04,... --email <financeiro descartável> --senha <senha> --saida <arquivo.json>
  põe <dir> em sys.path[0]; env do filho: DATABASE_URL, FLASK_ENV=development, MANTO_SEM_THREADS=1, MAIL_SUPPRESS_SEND=true, PYTHONUTF8=1, sem PYTHONPATH; cwd=<dir>; instala o disjuntor de rede; login por POST /api/auth/login.
  por mês: GET /api/financeiro/dashboard?period=custom&start=AAAA-MM-01&end=<último dia> e GET /financeiro/?period=custom&start=&end= (contexto capturado por template_rendered).
  saída: {"app_file": <caminho de app/__init__.py usado>, "sha": ..., "meses": {"AAAA-MM": {"api": {dre.realizado, dre.projetado, dre.total, kpis, receita_por_tipo, monthly_trend, recebimentos_previstos_total, nf_a_emitir_total, n_eventos}, "jinja": {drg_realizado, drg_projetado, drg_total, ticket_medio, a_receber_clientes, receita_por_tipo, monthly_trend, recebimentos_previstos_total, nf_a_emitir_total}}}}
No verify: BASELINE_SHA = '14cec75'; _arvore_main() -> Path (git archive + zipfile); _dump(raiz, meses) -> dict; _delta(a, b) -> dict.
Guardas: `app_file` de cada dump dentro da sua raiz; BASELINE ancestral de HEAD e != HEAD; pelo menos 12 meses comparados e um com receita > 0; mês com cancelado real no espelho é excluído e listado.
Exigência para a migration: só coluna nullable ou com server_default (o código da main precisa ler e gravar no banco migrado; é também o que torna o `git revert` seguro).

**Pontos de toque.**
- app/api/financeiro_read.py:183-264 (DRE da API), :239-240, :243-250 (gastos extras sem olhar categoria), :252, :365-385 (Tendência), :425-445, :449-466
- app/financeiro/routes.py:155-178 (_resolve_period: period=custom&start=&end=), :205-257 (_compute_drg), :260-263, :274-301, :305, :394-415, :533-575 (contexto do template)
- app/__init__.py:830-831 (blueprint Jinja registrado)
- app/calendar/cancel_ops.py:174-189 (devolução nasce aprovada, com expense_date de hoje e event_id)
- specs/263b-hotfix-proxy-vazamento-sockets/verify_263b.py:398-407
- migrations/versions/e5a1c7d93b20_formulario_destino.py (head atual)

**Riscos.**
- Evento que começa nos segundos entre os dois dumps troca de Realizado para Projetado: os dumps rodam em sequência e, se a diferença for só essa, com Total igual, repete uma vez.
- Se a main for mesclada na branch, `BASELINE_SHA` tem de ser atualizado para o novo merge-base no mesmo commit (tarefa no tasks.md).
- Antes do núcleo as duas árvores são iguais e o cenário 36 passa por construção: ele é guarda de regressão, não prova da feature; o verify imprime esse aviso enquanto `git diff --quiet BASELINE HEAD -- app/financeiro app/api/financeiro_read.py` não acusar diferença.
- Se os dois subprocessos importarem a mesma árvore, a comparação é vazia: a guarda do `app_file` e o −600 da main no cenário 26 são o que impede isso.
- Tempo: ~40 meses × 2 telas × 2 árvores; `--rapido` restringe a M−6..M+6 no dia a dia, o portão roda inteiro.

**Verify.** Cenário 26: API e Jinja iguais ao centavo dentro de cada árvore; Projetado com delta zero; controle S1−S0 no mês do evento = +2.000 (o evento contava antes de cancelar). Cenário 27: mês do evento com delta zero depois do cancelamento; para a Tendência, variante com evento em M−1 cancelado hoje — a linha de M−1 não tem os 2.000 na branch e tem na main. Cenários 28 a 35 reusam `_dump` só na branch. Cenário 35: abrir Comissões e Planilha (API e Jinja) entre dois dumps e a comissão do retido continuar 18. Cenário 30: depois do 'Salvar' em Gastos Extras, o dump não volta a somar a devolução.

**Revisão adversarial: parcial.** O mecanismo é viável. `git ls-tree -r 14cec75 app` dá 193 arquivos; nada em app/ importa módulo da raiz; `create_app()` cria `instance/` sozinho; o `.env` não é lido (só run.py e sync_worker.py chamam dotenv). Furos:

1. **S2−S0 não fecha em +342 nem em zero se a Planilha for aberta entre as medições.** Os cenários 23 e 35 abrem, e V4 manda abrir "entre dois dumps". O primeiro acesso à Planilha de um mês cria os recorrentes e os salários dele, e a DRE daquele mês muda em milhares de reais. V4 só tratou o relógio e o `ensure_recurring_entries(hoje)` do próprio dashboard.

2. **O contrato de chaves não bate com o payload.** `receita_por_tipo`, `monthly_trend` e `a_receber_clientes` ficam em `paineis`; `recebimentos_previstos_total` e `nf_a_emitir_total`, em `pendencias`. Faltam `paineis.a_receber_clientes` (cenário 33), `eventos` e `custo_nota_total`. Uma lista de chaves deixa passar mudança fora dela.

3. **Depois do núcleo a branch tem chaves novas** (linha do retido, card). Igualdade de dicionário inteiro falha em todo mês. O comparador não está definido.

4. **"API e Jinja iguais ao centavo" só vale para a cascata.** O ticket médio já difere por desenho (API divide a receita presencial; Jinja divide a receita bruta) e a Receita por Tipo também (a API soma a barra "Loja Virtual").

5. **As guardas olham o commit, mas o dump da branch roda o working tree.** Hoje HEAD é 14cec75, igual à constante; com o núcleo ainda não commitado o aviso "as árvores são iguais" mente.

6. **A Tendência é ancorada em hoje.** É idêntica em todo mês pedido: comparar 40 vezes é custo sem prova.

7. **Risco de travar.** `ensure_recurring_entries` usa advisory lock de transação. Subprocesso chamado com transação aberta no processo do verify pode esperar para sempre.

**Emenda.** - O aquecimento de V2 roda antes de S0 e antes do cenário 36. Os deltas são afirmados só nas linhas aditivas (`receita_bruta`, `cpv`, `comissoes`, `impostos`, `gastos_extras`, `resultado_liquido`), com `pessoal` e `gastos_recorrentes` afirmados em delta zero como controle.
- `dre_dump` grava o JSON inteiro da API e todo valor numérico do contexto Jinja. Comparador do 36: toda chave da main existe na branch com valor igual; chave só da branch tem de ser zero ou vazia em mês sem cancelamento.
- API × Jinja: igualdade só em `drg_realizado`, `drg_projetado` e `drg_total`.
- Guardas: `git merge-base --is-ancestor BASELINE HEAD`; o aviso usa `git diff --quiet BASELINE -- app` (working tree).
- Tendência comparada uma vez.
- `subprocess.run(timeout=...)`, chamado fora de `app.app_context()`.
- Árvore da main em `tempfile.mkdtemp()`, fora do repositório.

**Evidência da revisão.** app/api/financeiro_read.py:239-264, :287-295, :341-342, :365-385, :494-545 (formato real do payload). app/financeiro/routes.py:181-202, :205-257, :327-330, :394-415, :533-575. app/gastos/gastos_ops.py:498-543 (lock em :516). app/api/financeiro_read.py:680, :722. app/__init__.py:543-603, :831. specs/263b-hotfix-proxy-vazamento-sockets/verify_263b.py:398-407 (precedente usa `git show main:`). `git log --oneline -1` = 14cec75; `git status --short` mostra specs/303-sync-nao-apaga-venda/ ainda não versionada.

## V5 — (c) Como dividir o verify em blocos por história para falhar primeiro pelos motivos certos?

**Decisão.** Nove blocos, cada um com fixtures próprias semeadas no início do bloco e mês isolado próprio; a numeração dos cenários da spec é mantida. B0 Chão: travas, dublê, disjuntor, meses isolados vazios, cenário 36. B1 (H1): 1, 3, 4, 5, 6, 7, 7a, 13, 14, 15. B2 (H5): 8 e a variante antecipada, 9. B3 (H2): 2, 17. B4 (H3): 10, 10b, 11, 12, 16, 18. B5 (H4): 19, 20, 21, 22, 23, 23a, 23b, 23c. B6 (H6): 24. B7 (H7 + FR-032 + FR-037): 26 a 35 e a parte de dinheiro do 40. B9: 41. Os blocos de dinheiro (B5, B7) cancelam pelo botão da 224 em evento NÃO marcado, então não dependem do sync; só B2, B3, B4 e B6 precisam de evento marcado e viram BLOQUEADO enquanto H1 não existir. O verify é rodado uma vez ANTES do núcleo e a saída vai para o tasks.md: a lista fechada do que pode estar verde nesse momento é 7, 15, 36 e a metade 'COMERCIAL não cancela' do 11.

**Porquê.** A constituição pede que o verify nasça falhando pelos motivos certos e passe ao fim de cada história (constitution.md:155-159). A FR-021 diz que a regra do dinheiro vale para todo cancelamento, marcado ou não (spec.md:520-522): isso permite testar comissão e DRE sem depender da trava do sync. Fixtures por cenário impedem cascata: antes do núcleo, o sync de um mês isolado apaga os eventos ausentes daquele mês, e só eles — os eventos dos outros blocos estão presentes no dublê ou em mês não liberado. Cenário verde antes do núcleo fora da lista fechada é defeito do verify ('passa sem exercitar nada').

**Alternativas rejeitadas.** (1) Um verify por história (verify_303_h1.py ...): rejeitada — a convenção é um `verify_NNN.py` (constituição VI, artefatos mínimos), e dublê mais semeadura seriam duplicados sete vezes. (2) Ordem numérica da spec sem blocos: rejeitada — os cenários 10 a 18 misturam sync, RBAC e dinheiro, e uma história pela metade deixaria vermelhos sem dizer qual história falta. (3) Marcar o evento direto na coluna nova para desbloquear os blocos seguintes: rejeitada — o verify passaria a conhecer o nome da coluna e a pular o caminho real.

**Contrato.** BLOCOS = ['B0','B1','B2','B3','B4','B5','B6','B7','B9']; cada bloco é uma função `bloco_Bn()` que semeia e registra seus cenários com `cenario(nome, fn, bloco='Bn')`.
Mensagens de falha citam o requisito: 'FR-001: o sync apagou evento com venda', 'FR-018: o desconto caiu num repasse já liquidado'.
Checkpoints do tasks.md: fim de H1 -> `--ate B1`; fim de H5 -> `--ate B2`; ...; portão final -> sem argumentos.
Acréscimos à tabela da spec (sub-cenários, sem renumerar): 1b (evento passado com venda percebido pelo cleanup_past e pelo force_sync), 7b (pai vazio com ensaio que tem EventLog), 10b (trava da FR-024 ligada), 13 em quatro variantes, 27b (Tendência com evento em M−1), 40 dividido em 40a (FR-032 e FR-037, na 303) e 40b (card e ficha do talento, na 303b).

**Pontos de toque.**
- specs/303-sync-nao-apaga-venda/spec.md:661-706 (tabela de cenários; não existe cenário 25), :520-522 (FR-021)
- .specify/memory/constitution.md:155-169
- .specify/templates/tasks-template.md:15, :57 (verify na fase Foundational)
- specs/302-portal-detalhes-do-evento/verify_302.py:363-376 (controle contra passagem a vazio)

**Riscos.**
- O cenário 40 da spec mistura 303 e 303b; sem dividir em 40a/40b o verify da 303 nunca fecha verde.
- O bloco B0 lento (cenário 36) rodando a cada iteração desanima o uso: `--rapido` existe para isso.
- Se o núcleo mudar o que o botão da 224 faz com evento não marcado, B5 e B7 mudam junto — é o esperado pela FR-021.

**Verify.** B1 abre com a sonda que separa 'núcleo ausente' de 'núcleo errado': depois do sync o evento com venda ainda existe? B4 cenário 11 e B5 cenário 23b afirmam 403 exato para o COMERCIAL e 200 para o Superadmin na mesma rota. B3 cenário 17 afirma faixa vazia (200, sem erro) para FIGURINO e faixa vazia depois de resolvido — inclusive por cancelamento, que é a metade da FR-033 que não pode esperar a 303b.

**Revisão adversarial: parcial.** Os blocos por história e a independência de B5/B7 do sync (FR-021) se sustentam. Problemas:

1. **A lista fechada do que pode estar verde antes do núcleo está incompleta.**
   - Cenário 31 é verde hoje: a DRE soma todo gasto aprovado, então multa e devolução de evento vivo já "continuam em gastos extras".
   - As duas variantes de credencial do 13 são verdes hoje (ver V1).
   - Metades do 22 (a pagar vira cancelada) e do 27 (mês do evento sem o cancelado) já valem.
   Pela regra do próprio V5, isso é defeito do verify.

2. **`--ate Bn` não acompanha a ordem de construção de V6.** A fase 7 (H6, bloco B6) roda B5 (H4) antes de ele existir. A fase 6 (H3a) deixa 12, 16 e 18 de B4 vermelhos. "Cada fase termina com o seu `--ate` verde" é falso como escrito.

3. **O cenário 2 (sino) está em B3, mas V6 constrói o sino em H1.** O checkpoint de H1 não prova o que H1 entregou.

4. **A avaliação de cancelado (parte do 24) fica BLOQUEADA por H1** sem depender de evento marcado.

5. **Os sub-cenários novos** (1b, 7b, 10b, 13 em quatro, 27b, 40a/40b) só valem depois de entrarem na tabela da spec (Princípio VII).

**Emenda.** - Renumerar os blocos na ordem de construção: B1 H1 (com o cenário 2), B2 H5, B3 H2 (17), B4 H3a (10, 10b, 11), B5 H6 (24 e 24b), B6 H4, B7 H3b (12, 16, 18), B8 H7 + FR-032/037, B9 limpeza. Assim `--ate` é linear.
- O tasks.md traz, por fase, a lista esperada de verdes, vermelhos e bloqueados.
- Lista fechada de verdes antes do núcleo: 7, 15, 31, 36, a metade "COMERCIAL não cancela" do 11 e o sub-cenário "lista inteira falha" do 13. Os cenários 22 e 27 ganham asserção que falha hoje (ciclo do desconto fora de repasse liquidado; Tendência de M−1).
- 24b (avaliação de cancelado) vira cenário sem dependência de marca.
- Atualizar a tabela da spec antes do plan.md.

**Evidência da revisão.** app/api/financeiro_read.py:243-250 e app/financeiro/routes.py:294-301 (todo aprovado soma). app/calendar/service.py:135-137; app/calendar/sync.py:83-85. app/calendar/cancel_ops.py:139-155 (a pagar vira cancelada; paga vira estorno). app/api/financeiro_read.py:225-234, :369-373 (mês sem cancelado; Tendência sem o filtro). specs/303-sync-nao-apaga-venda/spec.md:661-706. .specify/memory/constitution.md:147-159.

## V6 — (d) Qual é a ordem de construção das histórias e o que é Foundational?

**Decisão.** Foundational (bloqueia tudo): (1) migration ÚNICA, aditiva, `down_revision = e5a1c7d93b20`, com as colunas da marca e as do cancelamento congelado — a 303b não tem migration; (2) modelos; (3) trava de escrita no Google (FR-024) em `app/config.py`; (4) `verify_303.py` + `dre_dump.py`, rodados vermelhos antes do núcleo; (5) ajuste do verify_205 (V9); (6) consulta tri-estado e lista paginada em `service.py`, como função nova, sem mudar `fetch_single_event`; (7) a função única do resumo do cancelado (FR-026). Histórias, em dois marcos. Marco A, o sync: H1 com FR-002, FR-003, FR-008 e a emissão do sino na mesma transação da marca → H5 → H2 (endpoint da faixa e AppShell) → 'Devolver ao Google' de H3 → H6. Marco B, o dinheiro: H4 (corpo do cancelar, comissão proporcional, BV negociado, ramo em `_sync_commission_payment`, alterar devolução, travas e correção de Gastos Extras, Planilha e Comissões) → o resto de H3 (cancelar marcado sem remover do Google, diálogo Tudo/Parte/Nada, devolução no evento, textos da FR-025) → H7 com FR-032 e FR-037. Depois: docs, telas e contagem do dia do deploy. H8 vai para a 303b.

**Porquê.** H1 é a perda em curso e tudo depende de o registro existir (spec.md:108-109). H5 é P2 na spec, mas a confirmação por id (FR-002/003) é pré-condição da marca: marcar sem confirmar acenderia a faixa a cada adiamento, então o miolo de H5 nasce com H1 e H5 só acrescenta 'aplicar a data nova' e 'desmarcar por id a cada ciclo'. A FR-008 vai com H1 porque, assim que um evento fica no banco sem par no Google, o 'Sincronizar' (sem gate de papel, agenda_write.py:621-636 → routes.py:4191-4208) e a edição passam a alcançá-lo. H4 vem antes do cancelar de H3 porque o diálogo mostra o efeito na comissão (FR-015) e o evento mostra o retido (FR-014). H7 vem depois de H4 porque a DRE lê o que o cancelamento gravou, nunca recalcula (FR-026). `fetch_single_event` tem dois outros consumidores (virtuais_ops.py:1679; routes.py:4203-4205): função nova evita regressão neles. O marco A deixa um ponto de corte coerente: evento preservado, avisado e devolvível, com o cancelar ainda na regra da 224.

**Alternativas rejeitadas.** (1) Ordem pura por prioridade da spec (H1, H2, H3, H4, H7, depois H5, H6, H8): rejeitada — H3 inteira antes de H4 obrigaria a escrever o diálogo de cancelamento duas vezes, e H1 sem o miolo de H5 marca adiamento como sumiço. (2) Dinheiro primeiro, por ser a metade maior: rejeitada — o que sangra é o sync. (3) Duas migrations (sync e dinheiro): rejeitada — dois heads a encadear numa branch só, sem ganho; aditiva e nullable, a migration única não amarra a ordem do código.

**Contrato.** Fases do tasks.md:
 1 Setup: constantes (kind da notificação), trava em config.
 2 Foundational: migration + modelos; verify_303.py + dre_dump.py (saída vermelha colada); verify_205; service.py (consulta tri-estado, lista paginada); resumo do cancelado (FR-026).
 3 H1 (+FR-002/003/008, +sino na transação da marca) -> `--ate B1`
 4 H5 -> `--ate B2`
 5 H2 -> B3
 6 H3a Devolver ao Google -> B4 (10, 10b, 11)
 7 H6 -> B6   [paralelizável com 5 e 6]
   == marco A ==
 8 H4 -> B5
 9 H3b Cancelar com devolução -> B4 (12, 16, 18)
 10 H7 + FR-032 + FR-037 -> B7
   == marco B: portão sem argumentos ==
 11 Polimento: docs 01/02/03/04/05, typecheck, ruff, telas, contagem do dia do deploy.
Assinatura de `_cleanup_stale_events(items, year, month) -> list[str]` preservada: tem quatro chamadores (sync.py:79; admin_config_write.py:104; routes.py:475; verify_205.py:810).

**Pontos de toque.**
- migrations/versions/e5a1c7d93b20_formulario_destino.py (head; conferir com `flask db heads` antes de escrever)
- app/config.py:121-142 (onde a trava nova nasce, ao lado da de convites)
- app/calendar/service.py:134-158, :181-191
- app/calendar/routes.py:341-390 (único ponto que apaga por sumiço), :4191-4208
- app/calendar/sync.py:74-85 (o loop do ciclo não faz rollback por mês)
- app/calendar/cancel_ops.py:128-155, :158-191, :236-319 (`remover_do_google` existe em :242, mas o endpoint não o passa: agenda_write.py:558-563)
- app/financeiro/comissoes_ops.py:816-839, :879-900 (o resync cancela a linha de evento cancelado)
- app/marketing/virtuais_ops.py:1665-1679 (consumidor de fetch_single_event)
- app/api/agenda_read.py:374-400 (lucro do cancelado desconta a devolução e o BV cheio), :431 (em aberto)

**Riscos.**
- O marco A sozinho em produção deixaria o cancelar de evento marcado tentando remover do Google e mostrando aviso de falha (cancel_ops.py:278-286); é cosmético, mas só vale publicar assim se o dono pedir (ver open_questions).
- A função do resumo (FR-026) é Foundational, mas só fecha quando H4 define o que fica congelado: nasce com assinatura e os campos de leitura (pago, devoluções, retido) e ganha comissão, BV e imposto em H4.
- H2 tem metade no backend de H1 (emitir na transação da marca): se for construída só na fase 5, o cenário 2 fica vermelho por desenho até lá.

**Verify.** Cada fase termina com o seu `--ate` verde e os blocos seguintes vermelhos ou bloqueados, nunca com erro de harness. Depois da fase 8, abrir Planilha e Comissões (API e Jinja) dentro dos cenários 19 a 23 antes de conferir a linha — é o resync que destrói a comissão do retido. Depois da fase 10, o B0 (cenário 36) precisa continuar verde: é a primeira vez em que as duas árvores diferem na DRE.

**Revisão adversarial: parcial.** A ordem sync → dinheiro, o miolo de H5 e a FR-008 dentro de H1, e a função nova em service.py (por causa dos outros dois consumidores de `fetch_single_event`) se sustentam. Problemas:

1. **"Lista paginada" como Foundational contradiz a spec.** A spec resolve a lista incompleta pela confirmação individual da FR-002 e manda registrar "a lista do mês sem paginação" como dívida no docs/05. Paginar é escopo que a spec não pediu.

2. **A função do resumo (FR-026) na fase 2 bloqueia H1.** H1 é "a única perda de dinheiro em curso", e o próprio V6 admite que a função "só fecha quando H4 define o que fica congelado". Ela é fundação do marco B, não de tudo.

3. **A rejeição de duas migrations por "dois heads" está errada.** Duas revisões encadeadas são uma cadeia linear. A migration única exige o modelo de dados do cancelamento congelado (H4) fechado antes de H1; se ele mudar, nasce a segunda de todo jeito.

4. **Checkpoints `--ate` incoerentes com os blocos** (ver V5).

5. **"Assinatura de `_cleanup_stale_events` preservada" deixa um ponto sem dono.** A resposta do "Limpar eventos fantasma" só conta removidos; os marcados precisam aparecer na mensagem.

**Emenda.** - Fase 2 (Foundational) só com o que o marco A precisa: migration, modelos, trava, verify + dre_dump, ajuste do verify_205 e consulta tri-estado por id. Sem lista paginada (fica a dívida do docs/05, como a spec manda).
- FR-026 abre o marco B, como primeira tarefa da fase de H4.
- Migration: uma só, desde que o `data-model.md` feche as colunas do marco B agora. Registrar que uma segunda migration encadeada é aceitável se o desenho de H4 mudar. Toda coluna nullable ou com `server_default`.
- `cleanup_past` devolve um campo novo e opcional `marcados` por mês; `removed` fica como está.
- Checkpoints conforme a renumeração de V5.

**Evidência da revisão.** specs/303-sync-nao-apaga-venda/spec.md:404-405, :775 (lista sem paginação vira dívida), :108-109 (prioridade de H1), :526-533 (FR-026). app/calendar/service.py:148-158, :181-191. app/marketing/virtuais_ops.py:1665-1679; app/calendar/routes.py:4203-4206. app/api/admin_config_write.py:104-116. app/calendar/sync.py:79-82. app/api/agenda_write.py:558-563, :621-636. migrations/versions/e5a1c7d93b20_formulario_destino.py.

## V7 — (d) A divisão em 303 e 303b é necessária pelo tamanho? O que NÃO pode ser separado?

**Decisão.** É necessária. 303 = FR-001 a FR-032 mais a FR-037 (grade 'Resultado do cancelamento' e o fim do 'em aberto'). 303b = FR-033, FR-034, FR-035, FR-036 e FR-038, sem migration, em pasta e verify próprios (`specs/303b-.../verify_303b.py`), como Nível 1 por tocar mais de um domínio e telas. A 303b só lê o que a 303 grava. Inseparáveis, todos dentro da 303: (1) FR-027 com FR-028; (2) FR-001/004 com FR-002/003 — marcar sem confirmar por id marca adiamento; (3) FR-001/004 com FR-008; (4) a marca com a faixa, o sino e o desmarcar por ciclo (FR-004, 006, 009, 010); (5) FR-016/017/018 com o ramo novo de `_sync_commission_payment` e a FR-020; (6) FR-013 com FR-015a e FR-015b — sem a correção do 'Salvar', a devolução some, e sem a trava da categoria a FR-028 não reconhece a devolução; (7) FR-019 com a Planilha nova e a antiga; (8) FR-026 antes de tudo que lê o resumo; (9) a metade da FR-033 que diz que a faixa não conta cancelado vai na 303, dentro do endpoint da faixa; (10) FR-014 com FR-037 e com os textos da FR-025 da tela do cancelado; (11) toda coluna nova, inclusive as que só a 303b lê.

**Porquê.** Não há staging e push é deploy. A 303 já toca agenda, notificações, financeiro, comercial, portal, uma migration e três rotas novas, com 36 cenários. A 303b mexe nas consultas de listagem da agenda que todo papel usa (`_query_month_events`, routes.py:182-209), na busca e nas fichas: separada, um `git revert` dela não traz de volta o sync que apaga venda nem a DRE de −600. A spec já prevê essa divisão e proíbe só separar FR-027 de FR-028 (spec.md:800-803). A FR-037 sai do intervalo sugerido porque a 303 entrega o bloco da devolução e do retido na tela do evento (FR-014) e conserta o texto dessa tela (FR-025): deixar ao lado a grade antiga com 'lucro' que desconta a devolução (agenda_read.py:374-400) e o chip 'em aberto' (agenda_read.py:431) seria a mesma tela dizendo duas coisas, e os dados saem da mesma função e do mesmo payload.

**Alternativas rejeitadas.** (1) Tudo numa 303 só: rejeitada — conferência de tela de umas quinze superfícies num deploy sem staging, e reversão que desfaz a trava do sync junto. (2) Divisão literal da Premissa, com a FR-037 na 303b: rejeitada pelo motivo acima; a Premissa delega o corte ao plano e só fixa FR-027 com FR-028. (3) 303b como correção de Nível 2: rejeitada — mais de um domínio exige Nível 1 (constitution.md:126-140).

**Contrato.** 303 (verify_303.py): cenários 1 a 24, 26 a 36, 40a, 41 e os sub-cenários de V5.
303b (verify_303b.py, independente, Google em modo 'estoura se alguém chamar' como verify_299.py:105-114): cenários 37, 38, 39, 40b e limpeza.
A 303b não cria coluna. Campos de payload que ela acrescenta (situação única no resumo do evento, card de cancelamentos na DRE e no Dashboard Comercial) nascem opcionais no TypeScript.
O endpoint da faixa, na 303, já filtra `cancelled_at IS NULL`.
Publicação: 303 num deploy; 303b num deploy seguinte, fora do horário.

**Pontos de toque.**
- specs/303-sync-nao-apaga-venda/spec.md:800-803 (Premissa do tamanho), :562-583 (FR-033 a FR-038), :539-546 (FR-027/028 inseparáveis), :701-705 (cenários 37 a 40)
- app/calendar/routes.py:182-209 (agenda Mês/Lista já esconde cancelado)
- app/api/agenda_read.py:70 (serialize_event_summary), :374-400, :431, :688 (serialize_event_detail)
- app/api/agenda_write.py:609-618 (GET de cancelamentos: só Superadmin hoje)
- .specify/memory/constitution.md:116-140

**Riscos.**
- Entre os dois deploys o cancelado continua sem selo na visão Dia e na busca, e dá para ligar ensaio, tag NFC ou grupo a ele — é o comportamento de hoje, não regressão, mas a 303b precisa sair logo em seguida.
- O card 'Cancelamentos do período' só chega na 303b: na 303 a DRE já mostra a linha do retido, sem o detalhamento por evento.
- A 303b mexe na página de Cancelamentos e na tela do evento que a 303 acabou de alterar: ela parte da main já com a 303 mesclada.

**Verify.** Na 303, o cenário 17 cobre 'faixa não conta cancelado' e o 40a cobre 'Resultado do cancelamento' 1.000 / 600 / 400 / 18 / 40 sem 'em aberto', mais o +400 do vendedor no mês do cancelamento e a ausência dos 2.000 no mês do evento (Dashboard Comercial, Performance da Home, /admin/desempenho, ficha da cliente). Na 303b: 37 (Mês, Lista e Dia com e sem 'Mostrar cancelados'; busca com selo; precedência cancelado > sumiu), 38 (vincular ensaio, NFC e grupo recusados, com controle positivo em evento vivo), 39 (FINANCEIRO lê a página e é recusado na escrita; FIGURINO recusado), 40b (card e ficha do talento).

**Revisão adversarial: parcial.** A divisão e a vinda da FR-037 para a 303 se justificam: a grade "Resultado" de hoje desconta a devolução e o BV cheio, e o chip "em aberto" sai do mesmo payload. Faltam três inseparáveis e o processo:

1. **FR-020 está no intervalo da 303 e inclui a página de Cancelamentos.** Ela tem de mostrar o mesmo valor de comissão do retido. Além disso `listar_cancelamentos` pega só a primeira devolução (`.first()`): com o complemento da FR-015a, entre os dois deploys a página de hoje mostraria a devolução errada. A FR-026 também manda essa página ler a função única.

2. **A precedência "cancelado > sumiu" é necessária em todo lugar onde a 303 expõe a marca**, não só na contagem da faixa. A visão Dia mostra cancelado hoje; um evento marcado e depois cancelado apareceria lá com "Sumiu do Google". Vale também para o aviso do portal.

3. **"303b como Nível 1" bate na Regra Zero.** O número de Nível 1 nasce do `/speckit-specify` (o hook aloca `max+1`, e "o alocador ignora sufixos"); sufixo é de hotfix de feature entregue, Nível 2. O desenho não diz como a pasta nasce, para onde `feature.json` aponta nem o que acontece com a História 8 e os cenários 37 a 40 na spec da 303.

4. **Mover a FR-037 diverge da Premissa "Tamanho".** É permitido (a Premissa delega ao plano), mas a spec muda primeiro (Princípio VII).

**Emenda.** - Backend da página de Cancelamentos entra na 303: `listar_cancelamentos` passa a ler o resumo da FR-026 (total devolvido somando todas as devoluções, estado, retido, comissão do retido), com campos novos opcionais no TypeScript. Colunas novas, filtros e leitura do FINANCEIRO (FR-038) ficam na 303b. Um cenário da 303 afirma que o total da página é a soma depois do complemento.
- Na 303 o serializador nunca expõe a marca em evento cancelado (`sumiu = marca preenchida E cancelled_at IS NULL`), no resumo, no detalhe e no portal. O cenário 12 afirma isso. O resto da FR-033 (situação única nas listas) fica na 303b.
- Processo: antes do plan.md, editar a spec.md da 303 (Premissa, História 8, FR-033..038, cenários 37..40, SC-008) dizendo o que sai. A 303b nasce como pasta `specs/303b-.../` criada à mão depois do merge da 303, com `feature.json` apontado e esteira completa rodada sobre ela, sem passar pelo hook. Registrar no plano que é a exceção que a própria spec previu, ou pedir ao dono um número novo.

**Evidência da revisão.** specs/303-sync-nao-apaga-venda/spec.md:517-519 (FR-020), :526-533 (FR-026), :489-497 (FR-015a/b), :562-564 (FR-033), :571-572 (o Dia mostra cancelado), :800-803. app/calendar/cancel_ops.py:339-350 (`.first()`). app/api/agenda_read.py:70 (`serialize_event_summary`), :374-400, :431. app/calendar/routes.py:182-209. .specify/memory/constitution.md:116-124, :126-140; .specify/extensions.yml:18-25.

## V8 — (e) Como fazer a contagem pré-deploy (eventos passados com dinheiro que já não estão no Google) em modo só leitura, e onde registrar?

**Decisão.** Script versionado `specs/303-sync-nao-apaga-venda/contagem_pre_deploy.py`, rodado na máquina local contra o `manto_local` recém-restaurado do dump das 02:00, lendo o Google real só com `events.list` e `events.get`. Não chama `create_app()`. A conexão do banco abre com `default_transaction_read_only=on`; a credencial é montada do `site_settings.google_token` e renovada só em memória (nunca `save_token`). Dois passos: (1) sonda — consulta os ids dos eventos já apagados por sumiço desde 01/08, tirados do `audit_logs` (`gcal:<id>` no detalhe das linhas `auto_deleted`), e anota o que o Google responde de verdade para evento apagado; (2) contagem — para cada mês anterior ao corrente com evento no banco, lista o mês com paginação, consulta por id cada ausente e classifica em ausência confirmada, mudou de data ou inconclusivo, e os confirmados em 'com dinheiro' (regra da FR-001) ou vazios. Roda agora, na fase de plano, com o resultado em `research.md` §Contagem pré-deploy, e de novo no dia do deploy, com o número na entrada da 303 no `docs/03`. Corte: mais de 5 eventos com dinheiro → a spec ganha a regra 'primeira rodada sem sino' antes do `/speckit-tasks`; até 5 → regra normal, e a lista vai ao dono antes do deploy.

**Porquê.** A spec manda o plano contar (spec.md:388-392). O que a contagem prevê é o primeiro clique em 'Limpar eventos fantasma', não o deploy: o ciclo automático limpa do mês corrente em diante a cada 10 minutos (sync.py:51-79), então o que sumiu nesses meses já foi apagado pelo código atual; meses passados só são varridos pelo botão (admin_config_write.py:92-106) e pela rota antiga (routes.py:470-476). A sonda vale tanto quanto a contagem: nada em `app/` trata hoje a resposta de evento apagado (service.py:181-191 devolve None para qualquer erro), e é ela que calibra o tri-estado do núcleo e os modos do dublê (V1). Local e sobre o dump porque a regra da casa é não conectar direto na produção para investigar (DEVELOPMENT.md:280-281), e o dump tem no máximo um dia. Sem `create_app` não há thread nem escrita acidental (o token real mora no espelho; DEVELOPMENT.md:102-108).

**Alternativas rejeitadas.** (1) Rodar no Shell/SSH do Render contra o banco de produção: rejeitada — código avulso no contêiner de produção com banco gravável, para um número que o dump da madrugada já dá. (2) Usar o modo de simulação do próprio núcleo: rejeitada para a primeira rodada, porque o núcleo ainda não existe e o resultado condiciona a spec. (3) Só `events.list` por mês, sem consulta por id: rejeitada — evento antecipado para outro mês entraria como sumido, e a lista de hoje não pagina (service.py:148-158). (4) `load_credentials()` do app: rejeitada — ele grava o token renovado no banco e em arquivo (service.py:128-130).

**Contrato.** Comando: `$env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe specs\303-sync-nao-apaga-venda\contagem_pre_deploy.py [--desde 2023-01] [--so-sonda]`
Antes: `scripts\db\refresh-local-db.ps1` e, depois dele, `flask db upgrade` de novo (o refresh desfaz a migration local da 303).
Banco: create_engine(url, connect_args={'options': '-c default_transaction_read_only=on'}); só SELECT.
Google: objeto que expõe apenas list (com list_next) e get; qualquer outro método levanta.
'Com dinheiro' em SQL, espelhando a FR-001: sale_value > 0, ou EventPayment, ou EventContract, ou EventRole com talent_id exceto (character_name='Técnico de Som' e talent_id=42), ou group_leader_id preenchido, ou ser líder de algum evento. Fora: cancelled_at preenchido, event_type VIRTUAL e ENSAIO.
Saída (stdout, nada gravado): resposta crua da sonda por id; meses varridos; ausentes; confirmados; mudaram de data; inconclusivos; com dinheiro (id, título, data, venda, recebido, escalados) e o total em R$; vazios.
Registro: research.md §Contagem pré-deploy (data, nome do dump, números, lista); repetição no dia do deploy -> docs/03, entrada da 303.

**Pontos de toque.**
- specs/303-sync-nao-apaga-venda/spec.md:388-392, :789-794 (caminhos que limpam)
- app/calendar/sync.py:51-79
- app/api/admin_config_write.py:92-106
- app/calendar/routes.py:383, :402-403 (o id do Google fica no detalhe do AuditLog), :470-476
- app/calendar/service.py:60-90, :93-132, :148-158, :181-191
- DEVELOPMENT.md:79-89 (refresh-local-db.ps1), :102-108, :280-281

**Riscos.**
- A regra 'com dinheiro' em SQL pode divergir da do núcleo: na rodada do dia do deploy, conferir a lista contra o que o verify prova (cenários 3 a 7a).
- Ids muito antigos podem responder 404 em vez de 'cancelled': a sonda cobre só os cinco apagados recentes; o núcleo trata as três respostas como ausência, como manda a FR-003.
- O refresh do espelho apaga o que estiver local: rodar antes de aplicar a migration, ou reaplicar depois.
- Evento passado já realizado que sumiu do Google só tem uma saída sensata, devolver ao Google; se forem muitos, são muitos cliques do Superadmin — a lista precisa chegar ao dono antes.

**Verify.** Não é cenário do verify (que nunca lê o Google real). O que a sonda devolver fixa os três modos de `GoogleFalso.apagados` e entra no research.md como fato conferido; se o Google responder algo fora de 404, 410 e status 'cancelled', o dublê e o cenário 1 ganham o quarto modo antes do núcleo.

**Revisão adversarial: parcial.** Script local, só leitura, sobre o dump restaurado e com sonda do formato real de "evento apagado": se sustenta. O id do Google fica mesmo no detalhe do AuditLog (`gcal:<id>`), e meses passados só são limpos pelo botão e pela rota antiga. Ressalvas:

1. **O corte "mais de 5" é inventado.** A spec diz "se forem muitos". Quem decide é o dono, olhando a lista.

2. **A classe "mudou de data" tem efeito externo que a contagem não mede.** No primeiro "Limpar eventos fantasma", aplicar a data nova passa por `sync_events`, que chama `_notify_accepted_roles`: e-mail de "evento alterado" a artista real, em evento antigo. A saída lista quantos mudaram de data, mas não quantos têm escalado com convite aceito.

3. **O precedente da casa** (`dados_pre_deploy_299.py`, só leitura, rodado no backend) não foi citado. A rejeição do caminho pela produção é defensável, mas deve ser justificada contra ele.

4. **A contagem não foi rodada** e bloqueia o `/speckit-tasks`. O desenho não diz quem roda nem que é pré-requisito.

**Emenda.** - Tirar o corte numérico. A saída vai ao dono como pergunta, com três números: eventos passados com dinheiro confirmados ausentes (quantidade, R$ e lista); eventos que mudaram de data com escalados de convite aceito (quantos e-mails sairiam); inconclusivos. O dono decide se entra "primeira rodada sem sino" e, se for o caso, "sem e-mail de mudança".
- A saída ganha a coluna "escalados com convite aceito" por evento que mudou de data.
- Registrar em `research.md` a comparação com `dados_pre_deploy_299.py` e por que aqui se usa o espelho (o script lê o Google, não só o banco).
- Marcar no plano: contagem rodada e respondida pelo dono é pré-requisito do `/speckit-tasks`.

**Evidência da revisão.** specs/303-sync-nao-apaga-venda/spec.md:388-392, :789-794. app/calendar/routes.py:383, :402-403 (`gcal:<id>`), :470-476, :2286, :2339-2342 (`_notify_accepted_roles` na atualização). app/calendar/sync.py:51-79. app/api/admin_config_write.py:92-106. app/calendar/service.py:60-90, :128-130, :181-191. specs/299-sem-valor-cobrancas/dados_pre_deploy_299.py:1-24.

## V9 — O que fazer com o verify_205, que chama `_cleanup_stale_events` com lista vazia sobre um mês real do espelho?

**Decisão.** Ajuste mínimo no verify_205, como tarefa Foundational da 303: antes do bloco V7, `gcal_service.load_credentials = lambda: None` (restaurado no fim, junto do `insert_event`). Com isso a consulta por id que a 303 passa a fazer volta 'inconclusiva', nada é apagado nem marcado, e o V7.2 (venda virtual não é apagada) continua provando o que provava. Registrar no `docs/05` que o verify_205, como está hoje, apaga do espelho todos os eventos não virtuais do mês da primeira venda virtual.

**Porquê.** O bloco V7 pega `virtuais[0].start_at` — um mês real — e chama `_cleanup_stale_events([], mes.year, mes.month)` com commit (verify_205.py:807-811). Hoje isso apaga do `manto_local` todo evento não virtual e não cancelado daquele mês. Depois da 303, a mesma chamada consultaria o Google REAL por id para cada evento real do mês, com o token da empresa, e aplicaria `sync_events` no que voltasse — com reconciliação de elenco e Maps. O módulo `gcal_service` já está importado ali (verify_205.py:550) e já é restaurado no fim (verify_205.py:1581), então o ajuste são duas linhas. Falta de credencial é inconclusivo pela FR-003.

**Alternativas rejeitadas.** (1) Deixar como está e só avisar: rejeitada — é leitura do Google real e escrita no espelho disparadas por um verify de outra feature. (2) Reescrever o V7 com mês isolado e o dublê da 303: rejeitada — refatoração lateral de um verify entregue; o ajuste mínimo basta.

**Contrato.** verify_205.py, antes da linha 782: `credenciais_original = gcal_service.load_credentials; gcal_service.load_credentials = lambda: None`; na restauração (junto da linha 1581): `gcal_service.load_credentials = credenciais_original`. Nenhuma outra mudança.
docs/05: uma linha de dívida registrando o efeito atual do V7.2 no espelho.

**Pontos de toque.**
- specs/205-loja-interacoes-virtuais/verify_205.py:550, :567-568, :782-814, :1581
- app/calendar/routes.py:341-390, :373-382 (venda virtual nunca é apagada)
- app/calendar/service.py:181-186 (sem credencial, a consulta devolve None)

**Riscos.**
- Os cenários do verify_205 depois do V7 usam `insert_event` falso e não precisam de credencial (o falso substitui a função inteira, verify_205.py:558-568); se algum precisar, a restauração sobe para logo depois do V7.2.
- O ajuste não conserta o efeito de hoje no espelho; quem conserta é a própria 303, ao exigir confirmação antes de apagar.

**Verify.** Rodar o verify_205 uma vez depois de H1 pronta: V7.1 e V7.2 verdes, e a contagem de eventos não virtuais daquele mês igual antes e depois, conferida por conexão separada. No verify_303, o cenário 15 cobre a mesma regra (cancelado e venda virtual ausentes do Google: comportamento de hoje, sem marca).

**Revisão adversarial: parcial.** O diagnóstico confere: o verify_205 chama `_cleanup_stale_events([], ano, mês)` sobre o mês do primeiro evento VIRTUAL do banco, com commit. Hoje isso apaga todo evento não virtual e não cancelado daquele mês do espelho. `gcal_service` já está importado ali e o stub de credencial é suficiente depois da 303 (credencial ausente é inconclusivo pela FR-003). Dois pontos:

1. **O ajuste não para o estrago de hoje.** Enquanto H1 não existir, cada execução do verify_205 continua apagando o mês. Existe caminho igualmente mínimo que resolve agora e depois: o verify da 224 passa como `items` todos os outros eventos vivos (`outros_vivos`), deixando de fora só o evento sob teste.

2. **Com credencial nula a V7.2 pode passar a vazio.** Se o núcleo confirmar por id antes de testar "é venda virtual", o ramo da venda virtual não é exercitado.

Fora do alcance de V9, mas do mesmo tipo: `scripts/db/verify_cancelamento_evento.py` (224, não versionado) cancela com o corpo antigo e ficará vermelho quando a escolha Tudo/Parte/Nada for obrigatória.

**Emenda.** Ajuste de quatro linhas no verify_205, como tarefa Foundational:
- em :810, trocar a lista vazia por `outros_vivos` (todos os eventos com `google_event_id` que não sejam VIRTUAL), molde de `scripts/db/verify_cancelamento_evento.py:259-269`;
- manter `gcal_service.load_credentials = lambda: None`, restaurado junto da linha 1581, como cinto.

Assim nada é apagado hoje nem consultado no Google depois, e o ramo virtual continua exercitado. Registrar no docs/05 o efeito antigo no espelho e o verify da 224 que envelhece.

**Evidência da revisão.** specs/205-loja-interacoes-virtuais/verify_205.py:550, :567-568, :782-814, :1581. app/calendar/routes.py:348-386 (`live_ids` vazio apaga o mês; virtual poupado em :373-382). scripts/db/verify_cancelamento_evento.py:163, :257-269. app/calendar/service.py:183-185.

## O que a frente deixou de decidir (revisão)

- E-mail assíncrono: `send_async` (app/email_service.py:25-63) dispara thread daemon. Falta decidir como o verify espera as threads antes de afirmar "zero e-mail" ou "um e-mail" e antes da limpeza. Sem isso os cenários 8 e 14 correm contra a thread.
- Aquecimento da Planilha: o primeiro acesso a um mês cria `SalaryPayment` e `RecurringExpenseEntry` (app/api/financeiro_read.py:680, :722), e a DRE lê os dois. Falta um passo em B0 que abra M−1..M+2 antes de qualquer dump, e a declaração desses restos no cenário 41.
- Guarda contra backend local ligado: em dev a thread de sync roda com `WERKZEUG_RUN_MAIN=true` (app/__init__.py:240-269) e falaria com o Google real sobre os eventos de teste; o horizonte estica até 2032 (app/calendar/sync.py:56-64). Falta abortar com exit 2 quando `site_settings.calendar_auto_sync_at` for recente.
- Cenário 13: as variantes de credencial precisam falhar depois de a lista responder (credencial por chamada). Como desenhado, passam a vazio antes e depois do núcleo.
- Contrato da trava da FR-024 com a frente de config: nome da chave, leitura em `current_app.config` a cada chamada e o que a resposta diz com a trava ligada (cenário 10b). O verify nasce antes do núcleo e depende disso.
- Comparador main × branch do cenário 36: a regra para chaves novas da branch, a comparação do payload inteiro em vez de lista de chaves e o alcance de "API = Jinja" (só os três `drg_*`).
- Blocos × fases: a numeração dos blocos não segue a ordem de construção, e o cenário 2 está fora do bloco da história que constrói o sino. Falta a tabela "por fase: verdes, vermelhos, bloqueados" para o tasks.md.
- Living Spec (Princípio VII): os sub-cenários novos (1b, 7b, 10b, 13 em quatro, 24b, 27b, 40a/40b), a vinda da FR-037 para a 303 e a saída da História 8 têm de entrar na spec.md antes do plan.md. Falta também dizer o que é o "verify cruzado" citado em specs/303-sync-nao-apaga-venda/spec.md:218 (proposta: cenários 23 e 35).
- Como a 303b nasce: pasta à mão ou número novo, para onde `.specify/feature.json` aponta e quando (depois do merge da 303). A Regra Zero diz que sufixo é de hotfix e que Nível 1 nasce do `/speckit-specify`.
- Backend da página de Cancelamentos na 303: a FR-020 e a FR-026 estão no intervalo da 303, e o `.first()` de app/calendar/cancel_ops.py:339-350 erra com o complemento da FR-015a.
- Precedência "cancelado vence a marca" em todo serializador em que a 303 expõe a marca (agenda, detalhe, portal), não só na contagem da faixa.
- Limpeza: filtros por (`entity_type`, `entity_id`) em `notifications` e `audit_logs`; `audit_logs` de evento já apagado por `detail LIKE 'gcal:v303%'`; comissão de beneficiário EducaManto real; satélite antes do líder; tabela ou FK nova que a frente de dados venha a criar (por SQL cru, já que o verify não importa nada da 303).
- Ciclo de vida do dublê: liberação de mês por bloco (context manager), `reset()` entre cenários, suporte a `pageToken`, `timeMin` e `timeMax`. Os itens inseridos pelo "Devolver ao Google" entram em `itens` com as datas do corpo.
- Helper de contexto Jinja dentro do verify, para a Planilha e as Comissões da tela antiga (cenários 23 e 35). O `dre_dump.py` cobre só a DRE.
- Verifies legados que o núcleo muda: `scripts/db/verify_cancelamento_evento.py` (corpo antigo do cancelar; `_cleanup_stale_events` no mês corrente) e `scripts/db/verify_151_excluir_sync.py` (Sincronizar de um evento). Não são versionados; falta registrar no docs/05 que envelhecem com a 303.
- Resposta do "Limpar eventos fantasma" (app/api/admin_config_write.py:104-116): hoje só conta removidos. Falta o campo opcional com os marcados e o cenário 1b afirmar a mensagem.
- A contagem pré-deploy ainda não foi rodada e pode mudar a spec ("primeira rodada sem sino", e-mail de mudança de data em evento antigo). Falta marcá-la como pré-requisito do `/speckit-tasks` e dizer quem a roda.
- Procedimento depois do `refresh-local-db.ps1`: reaplicar a migration da 303 antes do verify (V8 cita, V3 não). O `_coluna_existe` deve devolver exit 2 com essa instrução.
- Orçamento de tempo do portão: cerca de 160 requisições de DRE em subprocesso, mais as medições S0/S1/S2. Falta a meta de duração e o que `--rapido` garante, para o checkpoint por história não virar execução parcial que ninguém repete inteira.

## Perguntas em aberto da frente

- Ponto de corte do deploy: a ordem de construção deixa a metade do sync (evento preservado, faixa, sino, 'Devolver ao Google', aviso no portal) pronta antes da metade do dinheiro. Se o dinheiro atrasar, o dono quer publicar a primeira metade sozinha para parar de perder evento — com o 'Cancelar' ainda na regra de hoje da 224 — ou a 303 sobe inteira de uma vez? O plano funciona nos dois casos; muda só o dia do primeiro deploy.
- Resultado da contagem pré-deploy: ainda não foi rodada (esta frente é só leitura e não acessa banco nem Google). Se passar de 5 eventos passados com dinheiro ausentes do Google, a regra 'primeira rodada sem sino' entra na spec e o dono precisa aprovar a emenda antes do /speckit-tasks.