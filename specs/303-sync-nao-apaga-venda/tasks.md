---
description: "Tarefas da feature 303 — o sync não apaga evento com venda"
---

# Tasks: Evento com venda que some do Google fica no sistema, a equipe vê, e o Superadmin o devolve

**Input**: artefatos em `/specs/303-sync-nao-apaga-venda/`

**Pré-requisitos**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/api-endpoints.md](./contracts/api-endpoints.md),
[quickstart.md](./quickstart.md). Antes de cada fase, ler as notas do trecho em
[armadilhas.md](./armadilhas.md) — pegadinhas do código de hoje, com `arquivo:linha`.

**Verificação (OBRIGATÓRIA — constituição, Princípio VIII)**: `verify_303.py` é escrito na fase
Foundational, **antes** do núcleo, com o Google substituído por um dublê que falha fechado, e nasce
falhando pelos motivos certos (saída gravada em `verify_303_primeira_falha.txt`). Não existe pytest
neste repositório. **Nenhum verify lê ou escreve no Google de verdade**: o `manto_local` tem o token
real da empresa.

**Migration**: uma, aditiva e escrita à mão — `a7c3e91f4d28` (uma coluna e um índice parcial em
`calendar_events`). `flask db migrate` é proibido.

**Esta feature não toca em dinheiro.** Cancelamento com devolução, comissão sobre o retido, DRE e
selo de cancelado são das entregas seguintes (`entregas-2-e-3-rascunho.md`): se uma tarefa abaixo
parecer pedir algo disso, a tarefa está errada.

**Decisões do dono de 30/09** (spec §Clarifications, sessão dos checklists): comissão já paga **não**
segura o evento — apagado, ele gera o estorno contra o vendedor, como hoje; a vaga automática do
técnico de som nunca conta, com ou sem cachê ("se foi pago é porque foi realizado"); e no intervalo
até a segunda entrega quem retém pagamento de evento cancelado de verdade é o Superadmin, conferindo
a faixa antes de fechar a Planilha.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivo que nenhuma outra tarefa pendente da fase toca)
- **[Story]**: história da spec — US1, US2, US3, US5, US6 (a numeração da spec pula a 4)
- As linhas citadas (`arquivo:linha`) foram conferidas no código de 30/09 e andam a cada tarefa:
  localizar pelo conteúdo

## Ambiente de toda execução

```powershell
cd C:\Users\schim\Desktop\Manto_Platform
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
$env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'
```

O verify exige o backend local **parado** (sai com código 2 se perceber um sync recente); as telas
exigem o backend local **ligado**. Depois de `scripts\db\refresh-local-db.ps1` a migration local
some: repetir `flask db upgrade` e `python seed.py`.

---

## Phase 1: Setup

- [X] T001 [P] Em `app/constants.py`, acrescentar ao fim do arquivo (depois de
      `DEPARTURE_DEFAULT_LOCATION`, :567) um bloco `# Feature 303` com três constantes de texto, com
      os valores fixados no contrato: `SITUACAO_CANCELADO = 'cancelado'`, `SITUACAO_SUMIU_DO_GOOGLE
      = 'sumiu_do_google'`, `SITUACAO_EXCLUSAO_SOLICITADA = 'exclusao_solicitada'`. Comentário em
      pt-BR com o porquê: a situação única do evento tem precedência cancelado > sumiu do Google >
      exclusão solicitada e é resolvida no servidor, para nenhuma tela recombinar três campos.
      Armadilha: o arquivo já tem três constantes de outros domínios com o valor 'cancelado'
      (`FIGURINO_PROD_CANCELADO` :178, `VIRTUAL_ORDER_STATUS_CANCELADO` :335,
      `MOTIVO_FORA_CANCELADO` :457) — não reusar nenhuma. `ruff check` no arquivo. _Fonte: R10;
      FR-033 (parte); data-model §Leituras derivadas._
- [X] T002 [P] Em `app/config.py`, criar `_suppress_calendar_event_writes() -> bool` logo abaixo de
      `_suppress_calendar_invites` (:121-142), no mesmo molde e nesta ordem:
      `CALENDAR_SUPPRESS_EVENT_WRITES=true` trava em qualquer ambiente;
      `CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true` libera; senão, travado quando `_db_url()` é
      localhost, 127.0.0.1 ou sqlite. Na classe-base `Config` (:188), abaixo de
      `CALENDAR_SUPPRESS_INVITES` (:236): `CALENDAR_SUPPRESS_EVENT_WRITES =
      _suppress_calendar_event_writes()`. Nenhuma variável nova no painel de produção. Docstring com
      o porquê: cobre SÓ a devolução ao Google (sync, limpeza e 'Sincronizar' seguem lendo; criar,
      editar, excluir e cancelar seguem escrevendo — dívida); o núcleo a lê de `current_app.config`
      a cada chamada; o escape local cria evento de verdade na agenda da empresa, que a produção
      importa 5 minutos depois. Não tocar a trava de convites. _Cenários: faz passar o 18 e a
      afirmação da trava no 0._ _Fonte: R14; FR-024; Princípio XIV; data-model §Configuração._

---

## Phase 2: Foundational (bloqueia todas as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T003 [P] Criar À MÃO `migrations/versions/a7c3e91f4d28_evento_sumiu_do_google.py` (`flask db
      migrate` é proibido): `revision = 'a7c3e91f4d28'`, `down_revision = 'e5a1c7d93b20'` — head
      único conferido em 30/09 nas 136 migrations; reconferir com `flask db heads` ao escrever (a
      298b é da mesma onda). `upgrade()`: `op.add_column('calendar_events',
      sa.Column('google_missing_since', sa.DateTime(), nullable=True))` e
      `op.create_index('ix_calendar_events_google_missing_since', 'calendar_events',
      ['google_missing_since'], postgresql_where=sa.text('google_missing_since IS NOT NULL'),
      sqlite_where=<o mesmo>)`. Sem `UPDATE` e sem `server_default`. `downgrade()`: `drop_index` e
      `drop_column`. Molde: `b8e4d27a91f5_cancelamento_de_evento.py:25-65` (lá só há
      `postgresql_where`; aqui vão os dois). Docstring em pt-BR com o porquê: coluna própria em vez
      dos campos da 224; aditiva, nenhum evento existente muda. `ruff format` no arquivo novo.
      _Fonte: R1; data-model §Migration; plan §Constitution Check (Stack)._
- [X] T004 Em `app/models.py`, classe `CalendarEvent` (:236): acrescentar `google_missing_since =
      db.Column(db.DateTime, nullable=True)` depois do bloco da solicitação de exclusão (:291-295),
      com comentário do porquê: horário de parede de São Paulo sem fuso (`now_sp()`), como
      `cancelled_at`; `NULL` = não marcado; só `sumico_ops.marcar` e `desmarcar` escrevem; não reusa
      `deletion_requested_*` porque o Comercial sobrescreveria a marca e o 'Recusar' a zeraria. Em
      `__table_args__` (:238-241), acrescentar `db.Index('ix_calendar_events_google_missing_since',
      'google_missing_since', postgresql_where=db.text('google_missing_since IS NOT NULL'),
      sqlite_where=<o mesmo>)`, no molde de `Notification` (:624-628), para um autogenerate futuro
      não propor o drop. Armadilha: o índice parcial `ix_calendar_events_cancelled_at` da 224 não
      está declarado no modelo (drift antigo) — não consertar de passagem. _Fonte: R1; data-model
      §calendar_events._
- [X] T005 Em `app/models.py`, `CalendarEvent`, logo depois de `has_pending_deletion_request`
      (:392-395), criar três propriedades sem consulta extra: `is_google_missing -> bool` (marca
      preenchida E `cancelled_at` nulo); `situacao -> str | None`, com precedência
      `SITUACAO_CANCELADO` > `SITUACAO_SUMIU_DO_GOOGLE` > `SITUACAO_EXCLUSAO_SOLICITADA` > `None`;
      `situacao_desde -> datetime | None` (`cancelled_at`, `google_missing_since` ou
      `deletion_requested_at`, conforme a situação). Importar as três constantes no bloco `from
      .constants import (...)` do topo (:12-30). Docstrings com o equivalente SQL de 'marcado'
      (`google_missing_since IS NOT NULL AND cancelled_at IS NULL`) e o aviso de que o predicado de
      consulta mora em `sumico_ops.filtro_marcados()` — a propriedade serve a objeto já carregado. A
      marca nunca aparece em evento cancelado. `ruff check app/models.py`. _Fonte: R10; FR-033
      (parte); data-model §Leituras derivadas._
- [X] T006 `migrations/versions/a7c3e91f4d28_evento_sumiu_do_google.py` — Aplicar a migration no
      `manto_local`, na ordem real do deploy: com `DATABASE_URL` de `.local-db-url`,
      `FLASK_ENV=development` e `MANTO_SEM_THREADS=1`, rodar `.venv\Scripts\flask.exe db upgrade` e
      depois `.venv\Scripts\python.exe seed.py`. Conferir: head `a7c3e91f4d28`;
      `calendar_events.google_missing_since` existe e está nula em todos os eventos;
      `ix_calendar_events_google_missing_since` existe como índice parcial; nenhum evento muda de
      comportamento. Armadilha: `scripts\db\refresh-local-db.ps1` desfaz a migration local — depois
      de qualquer refresh do espelho, repetir este passo antes do verify (que sai com exit 2 quando
      a coluna não existe). _Fonte: quickstart §2; plan §Constitution Check (Operação e Deploy)._
- [X] T007 Em `app/calendar/service.py`, logo abaixo de `fetch_single_event` (:181-191, que NÃO
      muda: o Meet da Loja Virtual depende dela), criar `@dataclass(frozen=True) class
      ConsultaEvento(desfecho, item=None, motivo='')` e `consultar_evento(calendar_id,
      google_event_id) -> ConsultaEvento`, que nunca levanta: o `try` envolve também
      `load_credentials()` e `build()` (exceção ao carregar a credencial, ou
      `google.auth.exceptions.RefreshError` em QUALQUER ponto — inclusive no `.execute()`, que é
      onde a renovação acontece hoje: `save_token` não grava `expiry`, então o ramo de renovação de
      `load_credentials` (`service.py:128`) nunca dispara e o 401 é renovado dentro do
      `google_auth_httplib2`; o `except RefreshError` vem antes do `except Exception` →
      `sem_credencial`; qualquer outra que não seja erro HTTP → `rede`; não há cliente compartilhado
      entre consultas). Ausente: HTTP 404 (`http_404`), 410 (`http_410`) ou item com `status ==
      'cancelled'` (`cancelled`) — conferido ANTES do início, porque o Google devolve o apagado com
      HTTP 200 e dados completos. Presente: item com `start.dateTime` ou `start.date`; motivo vazio
      ou `serie_recorrente` (item com `recurrence`). Inconclusivo: `sem_credencial` (ausente, falha
      ao renovar, 401), `rede`, `http_5xx`, `http_403`, `http_429`, `http_4xx`, `sem_inicio`.
      Desfechos e motivos como constantes do módulo; status por `HttpError.status_code`;
      `logger.warning` no inconclusivo, sem AuditLog. _Fonte: R3; FR-002; FR-003; contrato §Google._
- [X] T008 Em `app/calendar/service.py`, `insert_event` (:217-263): acrescentar o parâmetro
      só-por-nome `*, all_day: bool = False` depois de `conference_request_id` (:224). Com
      `all_day=True`, o corpo (:242-247) leva `start = {'date': start_dt.date().isoformat()}` e `end
      = {'date': end_dt.date().isoformat()}` — sem `timeZone` e sem somar um dia: o fim de dia
      inteiro já é gravado exclusivo no banco (`parse_event_datetime`, :203-205). Com `False`, o
      corpo fica idêntico ao de hoje. Documentar no docstring. Não mexer nos cinco chamadores
      (`event_ops.py:1642`, `routes.py:2584` e `:4037`, `agenda_write.py:812`,
      `virtuais_ops.py:1179`) nem em `update_event` e `upsert_task_event`. Quem decide `all_day` é o
      núcleo da devolução (fase 6). `ruff check` no arquivo. _Fonte: R13 (dia inteiro); FR-012;
      contrato §Google._
- [X] T009 `specs/303-sync-nao-apaga-venda/verify_303.py` — Criar `verify_303.py` — esqueleto, no
      molde de `verify_302.py:53-135` e `:704-739`: docstring com os cenários da tabela da spec, o
      comando, os efeitos no espelho e a receita da conferência de tela (quickstart §4); saída
      UTF-8; `REPO_ROOT` no `sys.path`; `setdefault` de `FLASK_ENV`, `MANTO_SEM_THREADS`,
      `MAIL_SUPPRESS_SEND`; `create_app()`, `TESTING`, `limiter.enabled = False`. Constantes
      copiadas do contrato: coluna da marca, chave da trava, kind do sino, ações de auditoria e
      `ROTAS` (dicionário). O verify não importa NADA que a 303 cria; a coluna é lida por SQL cru.
      `_no_banco` em conexão separada. `cenario(nome, fn, bloco=)` com três estados — OK, FALHA,
      BLOQUEADO (`class Bloqueado`) — e `rollback` sempre. `--ate Bn` (B0 a B5; o B9 roda sempre);
      `--semear-tela` e `--limpar-tela` ficam reservados para a tarefa própria. `main()` com
      `try/finally`; exit 1 com FALHA ou BLOQUEADO, 2 para ambiente; fim em `N/N OK`. _Fonte: R18
      (d, e); plan §Constitution Check VIII; quickstart §3._
- [X] T010 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, classe
      `GoogleFalso`, instalada em `cal_service.build` e `cal_service.load_credentials` — os dois
      nomes que toda função do service resolve na chamada (`service.py:135-139, 183-186, 238-241,
      276-279, 364-367`); trocar função por função deixaria escapar os bindings de
      `routes.py:19-29`. `events().list/get/insert/patch/delete` e `list_next`, com `.execute()`,
      todos registrados em `chamadas`. Falha fechado: `list` de mês não liberado e `get` de id
      desconhecido levantam `HttpError` 503 real (molde `verify_205.py:1296-1314`). `list` honra
      `timeMin`, `timeMax`, `pageToken` e página cortada. Quatro modos de apagado: cancelado
      completo, cancelado mínimo, 404, 410. Falhas por id e pela próxima consulta DEPOIS de o `list`
      de um mês indicado responder (armada nesse momento, nunca antes: depois da História 5 a
      reconferência dos marcados roda antes do laço de meses e consumiria a falha) — 5xx, 403, 429,
      `TimeoutError` e `google.auth.exceptions.RefreshError` levantado no `.execute()` do `get` (o
      caminho real do token revogado); credencial por chamada (ausente, `RefreshError`), contada do
      mesmo jeito; gancho por id dentro do `get`; `liberar(mes)` por bloco; `reset()`. Itens SEM
      `created` e COM `htmlLink` (sem ele o link nulo do marcado, no 1, passaria a vazio); `insert`
      devolve `v303g-N` e registra o item. _Fonte: R18 (a); spec §Verificação; R17 (sonda)._
- [X] T011 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`: (1) disjuntor de
      rede — embrulhar `socket.socket.connect` e `connect_ex`; host que não seja `127.0.0.1`, `::1`
      ou `localhost` é anotado em `rede_bloqueada` e levanta; (2) dublês do que não é Google:
      `cal_routes._lookup_sp_status` (ViaCEP; chamado em `routes.py:2279` e `:2328`),
      `cal_routes._fetch_travel_data` (`:2283`, `:2332-2335`), `maps.cidade_do_endereco`,
      `formularios_ops.retry_auto_link_pending` (import tardio em `sync.py:91`) e `es._send`
      capturando em `_emails` (`email_service.py:980` — é ele que confere a trava, então a captura
      vê todo e-mail); (3) `_esperar_threads()`: `join` com timeout em toda thread viva que não seja
      a principal, chamado antes de qualquer afirmação sobre `_emails` e antes da limpeza — o e-mail
      de mudança de data e o alerta de ensaio saem por `send_async` (`email_service.py:63`;
      `event_ops.py:75, 81`). _Fonte: R18 (b, f); spec §Verificação._
- [X] T012 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, guarda de ambiente
      antes de qualquer semeadura, saindo com exit 2 e a instrução do que fazer: `DATABASE_URL` que
      não seja localhost ou 127.0.0.1; coluna da marca inexistente (`information_schema` — 'rode
      `flask db upgrade`; o refresh do espelho desfaz a migration');
      `site_settings.calendar_auto_sync_at` com menos de 15 minutos — backend local ligado, cuja
      thread falaria com o Google real sobre os eventos de teste (o carimbo é UTC: `sync.py:140`);
      mês isolado com evento cujo `google_event_id` não começa por `v303`; evento marcado fora de
      `v303%` (uma limpeza local lê o Google real e pode ter marcado evento do espelho, que a faixa
      do 17 e a reconferência contariam: refresh do espelho e `flask db upgrade`). Guardar
      `site_settings.calendar_sync_cache` no início e restaurá-lo no `finally`: `_mark_month_synced`
      mantém só 24 meses (`routes.py:153-163`) e os meses de teste expulsariam os reais. _Fonte: R18
      (g); spec cenário 0; quickstart §0._
- [X] T013 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, fixtures de
      calendário e de gente. Meses isolados como constantes, um conjunto por bloco, de 2031 em
      diante; um mês além do horizonte do ciclo (o ciclo vai até o último evento do banco + 1 mês,
      `sync.py:51-64`); e `MES_PASSADO` calculado — o mês anterior ao evento mais antigo do espelho
      (constante fixa abortaria sempre se houvesse evento real lá). `_usuario(sufixo, papel)` (molde
      `verify_299.py:156-166`): Superadmin, Comercial (também vendedor), Figurino, Financeiro e
      revendedor EducaManto descartáveis, e-mail `v303-…@manto.local`. `_talento(sufixo)` (molde
      `verify_302.py:177-189`). `_chamar(email, metodo, url, corpo)`: login só por `POST
      /api/auth/login` (talento: `POST /api/portal/auth/login`), sempre FORA de `app.app_context()`.
      _Fonte: R18 (c); spec §Verificação._
- [X] T014 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, semeadura de
      eventos. `_evento_google(nome, quando, …)`: registra o item no dublê e o importa por
      `cal_routes.sync_events([item])` — Coordenador, personagens do título e, em SHOW, as vagas de
      som nascem do sistema; id `v303-<nome>`; o marcador `[TESTE verify 303] pode apagar` vai na
      DESCRIÇÃO (o título vira personagem: `routes.py:1923-1932`). `_escalar(event_id, talento_id,
      vaga=None)` só preenche vaga existente com `talent_id IS NULL`; exceção única, a do 7a: a vaga
      'Técnico de Som' do SHOW nasce com o talento 42 (`routes.py:2073-2078`) e recebe o descartável
      por UPDATE, nunca por INSERT (`_escalar(..., vaga='Técnico de Som', substituir_42=True)`).
      `_venda`, `_comprovante` (aceita valor nulo), `_contrato`, `_grupo(lider, satelite)`. INSERT
      direto só para o que o sync não cria: ensaio-filho com `EventLog`, venda virtual, evento
      cancelado recente. Execução: `_ciclo()` (`run_calendar_sync`), `_limpar_fantasmas(email)`
      (`POST /api/admin/sync/run`), `_marca(event_id)` por SQL cru e `_precisa_marcado(event_id)`,
      que levanta `Bloqueado('depende da História 1')`. _Fonte: R18 (c, d, e); CLAUDE.md §4
      (EventRole)._
- [X] T015 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, `limpar()`, chamada
      no início (restos de execução quebrada) e no `finally`. Acha os eventos por `google_event_id
      LIKE 'v303%'` — nunca pelo título: na `main`, o 'Sincronizar' o troca por 'Sem título'. Ordem:
      `rollback`; `notifications` por `entity_type = 'calendar_event'` E `entity_id` dos eventos de
      teste (os já apagados ficam guardados em memória) — nunca por id ou kind soltos;
      `commission_payments` pelo vendedor descartável (o estorno fica sem `event_id`); por evento,
      filhos e satélites antes: `_clear_event_side_tables` (`routes.py:259`) e `delete`;
      `audit_logs` por `entity_type = 'agenda'` + id, por `detail LIKE 'gcal:v303%'` e os de
      `auto-sync` criados desde o início da execução (UTC); talentos; `roles.clear()` antes de
      apagar cada usuário; chave da trava de volta a `True`. _Fonte: R18 (h); spec cenário 41._
- [X] T016 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B0. Cenário 0:
      `app.config['MAIL_SUPPRESS_SEND'] is True`; `app.config['CALENDAR_SUPPRESS_EVENT_WRITES'] is
      True`; `cal_service.build` e `cal_service.load_credentials` são os do dublê; meses isolados
      vazios; backend local desligado (a guarda passou); o disjuntor recusa um host externo de prova
      e o anota (a anotação é zerada em seguida). Cenário 18: carregar `app/config.py` em processo
      filho com o ambiente de cada caso (molde `verify_269b.py:94-118`) — banco local → travado;
      banco remoto → liberado; remoto com `CALENDAR_SUPPRESS_EVENT_WRITES=true` → travado; local com
      `CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true` → liberado. Armadilha: o filho herda
      `FLASK_ENV=development`; com `production` o `config.py` gravaria `instance/.secret_key`
      (:163-185). _Cenários: escreve 0 e 18 (verdes desde a primeira execução)._ _Fonte: spec
      cenários 0 e 18; R14; FR-024._
- [X] T017 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B1, cenários 1
      e 1b. Cenário 1, em quatro eventos com venda, comprovante, contrato e talento descartável numa
      vaga do título, um por modo de apagado do dublê: depois de `_ciclo()`, por conexão separada, o
      evento existe com venda, comprovante, contrato e escala intactos e a marca tem a data de hoje
      (São Paulo); `EventLog` e `AuditLog` `sumiu_do_google` dizem o que estava preso; zero e-mail
      em `_emails` depois de `_esperar_threads()`; e os payloads: `GET /api/agenda`,
      `/api/agenda/day/<data>` e `/api/agenda/search` devolvem `situacao: 'sumiu_do_google'` para o
      evento, e `GET /api/events/<id>` devolve `sumiu_do_google.desde` e `google_html_link` nulo, e
      um evento de controle não marcado do mesmo mês devolve o link preenchido. É a sonda do bloco:
      evento apagado = 'FR-001: o sync apagou evento com venda'. Cenário 1b, evento com venda em
      `MES_PASSADO`: `cleanup_past` como Superadmin → fica e é marcado; a linha do mês em
      `results[]` traz `marcados`, `movidos`, `desmarcados`, `inconclusivos`, `falhas`, e a
      `message` os seis números; o mesmo POST como Comercial → 403 (deve falhar). _Cenários: escreve
      1 e 1b (nascem vermelhos)._ _Fonte: spec cenários 1 e 1b; FR-001; FR-004; FR-023; FR-042; R2;
      R6._
- [X] T018 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B1, cenários 2
      e 2b. Cenário 2 (o evento do 1; `_precisa_marcado`): ler antes o número de destinatários com
      `resolver_destinatarios((COMERCIAL, SUPERADMIN))` (`notificacoes_ops.py:82-98`); rodar o ciclo
      mais duas vezes; por conexão separada: exatamente uma notificação `evento.sumiu_google` de
      `calendar_event` por destinatário, nenhuma nova nas repetições, zero para o Figurino
      descartável. Cenário 2b (corrida): gancho no `get` do dublê para o id — dentro dele, OUTRA
      conexão grava um carimbo distinto em `google_missing_since` e comita. Depois da limpeza: o
      carimbo é o da outra conexão; nenhum `EventLog` de sumiço, nenhum `AuditLog`
      `sumiu_do_google`, nenhuma notificação; `falhas` do mês igual a zero. Gancho que não dispara =
      'FR-002: a limpeza não consultou o evento'. _Cenários: escreve 2 (nasce bloqueado) e 2b (nasce
      vermelho)._ _Fonte: spec cenários 2 e 2b; FR-010; R6; R7._
- [X] T019 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B1, cenários
      3, 4, 5 e 6 — um evento por caso, todos SEM venda, removidos do dublê e limpos no mesmo ciclo.
      3: comprovante com valor e, em outro evento, comprovante com `amount` nulo. 4: contrato. 5:
      talento descartável na vaga de personagem que o sync criou do título. 6: líder e satélite de
      um grupo comercial, sem mais nada próprio, os dois ausentes. Afirmação comum, por conexão
      separada: o registro existe, a marca está preenchida e o `AuditLog` `sumiu_do_google` diz o
      que segurou o evento. Evento apagado = FALHA citando a FR-001. _Cenários: escreve 3, 4, 5 e 6
      (nascem vermelhos)._ _Fonte: spec cenários 3, 4, 5, 6; FR-001; R2._
- [X] T020 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B1, cenários
      7, 7a e 7b. O 7 em duas linhas, para a lista fechada ser conferível: '7 (apagado)' — evento
      vazio (só vagas sem talento) em cada um dos quatro modos de apagado e SHOW só com o técnico de
      som automático somem do banco; '7 (auditoria)' — o `AuditLog` `auto_deleted` traz o que o
      Google respondeu e o retrato vazio. 7a, dois SHOW: vaga 'Técnico de Som (Presença)' com
      talento descartável; talento descartável no lugar do 42 em 'Técnico de Som' — ficam e são
      marcados. 7b: pai vazio com ensaio-filho (INSERT direto, em mês não liberado) que tem
      `EventLog`; variante A some do Google; variante B `DELETE /api/events/<id>` como Superadmin →
      pai e ensaio apagados sem erro, e zero `get` para o id do ensaio. _Cenários: escreve 7, 7a e
      7b (só '7 (apagado)' nasce verde)._ _Fonte: spec cenários 7, 7a, 7b; FR-001; FR-007; FR-023;
      R2; spec §Casos de borda (evento vazio com ensaio)._
- [X] T021 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B1, cenário 13
      — cada variante com três candidatos com dinheiro num mês liberado e a falha injetada na
      PRÓXIMA consulta DEPOIS de o `list` do mês-alvo responder ('exatamente uma consulta no mês'
      conta os `get` feitos depois desse `list`; a ordem dos candidatos não é contrato). Erro 5xx,
      `TimeoutError`, credencial ausente e `RefreshError` — a credencial só cai depois de a lista do
      mês responder — → nada apagado nem marcado e exatamente uma consulta no mês; controle em cada
      uma: refeito com ausência confirmada, o mesmo evento é marcado; na variante 5xx rodada por
      `_ciclo()`, o `detail` do último `AuditLog` de `auto-sync` (conexão separada) traz, antes do
      primeiro `AAAA-MM:`, a frase `Sumiços:` com `0 com falha` e ao menos `1 sem confirmação` —
      nunca afirmar o status do ciclo, que no verify sai sempre `sync_erro` (armadilhas, Setup). 403
      e 429 na primeira consulta → os demais são consultados e marcados. Dois meses seguidos com a
      falha no primeiro → o segundo volta a consultar. Linha própria '13 (a lista inteira falha)':
      nada muda. A falha na reconferência dos marcados é o cenário 13d, no bloco B2. _Cenários:
      escreve 13 (só '13 (a lista inteira falha)' nasce verde)._ _Fonte: spec cenário 13; FR-003;
      FR-040; R4 (disjuntor local da chamada); R12._
- [X] T022 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B1, cenários
      13b e 13c. 13b: três candidatos com dinheiro no mesmo mês; `notificacoes_ops.emitir` (`:101`)
      embrulhado para levantar uma vez quando `kind == 'evento.sumiu_google'`, restaurado no
      `finally`. Depois do 'Limpar eventos fantasma': exatamente um candidato sem marca e sem
      notificação; a linha do mês vem com `ok: false` e `falhas: 1`; os outros dois marcados e
      avisados; na rodada seguinte o terceiro é marcado, com um aviso por destinatário; numa
      variante pelo `_ciclo()`, a frase `Sumiços:` do `detail` do `AuditLog` do ciclo diz `1 com
      falha`. 13c: dois meses liberados seguidos; no primeiro, um item novo cujo local-sentinela faz
      o dublê de `_lookup_sp_status` executar SQL inválido na sessão do app (erro de banco dentro de
      `sync_events`, `routes.py:2279`). Depois do ciclo: o segundo mês importou o seu item novo e
      marcou o seu candidato; nenhum evento de teste tem marca sem notificação. Variante pelo
      `_limpar_fantasmas(<superadmin>)` (o primeiro mês precisa de um evento de teste no banco,
      senão o `cleanup_past` não o visita): a linha do primeiro mês vem com `ok: false` e a do
      segundo com `ok: true`, com o item importado e o candidato marcado. _Cenários: escreve 13b e
      13c (nascem vermelhos)._ _Fonte: spec cenários 13b e 13c; R18 (falha por evento e erro de
      banco); R4; plan §Rastreamento de complexidade (IV)._
- [X] T023 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B1, cenários
      14 e 15. O 14 em três linhas. '14 (edição)' (`_precisa_marcado`): `PATCH /api/events/<id>`
      trocando título e data e `PATCH …/basico` trocando o tipo para SHOW e de volta → 200 (os
      avisos da troca de tipo, `event_ops.py:440-442` e `:479-484`, são esperados e provam que a
      automação rodou), sem a frase 'Não foi possível sincronizar a mudança com o Google Agenda.' em
      `warnings`, nunca 409; zero `patch` no dublê; a marca continua. '14 (Sincronizar, marcado)' e
      '14 (Sincronizar, não marcado)': evento ausente, um no modo cancelado completo e outro no
      mínimo; `POST /api/events/<id>/sync` → 409 'Este evento não está mais no Google Agenda. Nada
      foi alterado.'; título, datas e vagas iguais por conexão separada; zero e-mail. Um evento por
      chamada: na `main` o mínimo vira 'Sem título' e perde as datas. 15: evento cancelado
      (`cancelled_at` por UPDATE direto) e venda virtual (INSERT, tipo `VIRTUAL`) ausentes do dublê
      → existem, sem marca, zero `get` para os dois ids. _Cenários: escreve 14 e 15 (o 15 nasce
      verde)._ _Fonte: spec cenários 14 e 15; FR-008; FR-039; R11._
- [X] T024 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B2, cenário 8
      — cada variante com venda, comprovante e talento descartável. (a) `google.mover(id, …)` para
      um mês posterior liberado; (b) antecipado para `MES_PASSADO`, que o ciclo nunca lista; (c)
      movido para o mês além do horizonte, não liberado. Depois do ciclo: o MESMO `id` de banco, com
      a data nova, venda e comprovante intactos, sem marca e sem notificação. (d) presente, sem
      mudança e fora da lista (página cortada), em três itens — com '+ Coordenador' no título do
      Google, de dia inteiro, sem descrição —, por dois ciclos seguidos: nada muda, nenhum e-mail, o
      mês não o conta em `movidos` e há uma só linha `presente_fora_da_lista` por evento. Na `main`
      o evento é apagado e reimportado com outro `id`. _Cenários: escreve 8 (nasce vermelho)._
      _Fonte: spec cenário 8; FR-002; FR-041; R5; SC-002._
- [X] T025 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B2, cenário 9
      (`_precisa_marcado` em todos). (a) marcado volta à lista do mês (`google.restaurar`), e a
      rodada é o `_limpar_fantasmas` (sem reconferência, para exercitar a volta pela lista — pelo
      `_ciclo()` quem desmarcaria é a reconferência), com `desmarcados: 1` na linha do mês em
      `results[]` → marca nula, aviso do sino lido (`read_at`), `EventLog` 'Reapareceu no Google
      Agenda' e `AuditLog` `google_reapareceu`; zero e-mail. (b) marcado de `MES_PASSADO` restaurado
      → achado pelo próprio id, sem o mês ser listado. (c) marcado, editado no sistema (`PATCH`) e
      restaurado no Google com a data em outro mês → mesmo registro, com título e data do Google.
      (d) some de novo → marca nova e uma notificação NOVA por destinatário. (e) marcado presente no
      dublê e `POST /api/events/<id>/sync` como Comercial → 200, marca nula, aviso lido e `EventLog`
      com o nome de quem clicou. Cenário 13d: a primeira consulta da reconferência falha com 5xx →
      houve a consulta, nenhuma marca foi retirada, e os meses liberados listam, sincronizam e
      limpam. _Cenários: escreve 9 e 13d (nascem bloqueados)._ _Fonte: spec cenários 9 e 13d;
      FR-006; FR-010; R12; R7._
- [X] T026 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B3, cenário
      17, sobre `GET /api/events/sumidos-google`. Linha '17 (quem não vê)', sem depender de marca:
      Figurino, Financeiro e revendedor EducaManto → 200 com `pode_ver: false`, `total: 0`, `items:
      []`, nunca 403 (o 'deve falhar' é o Figurino não ver). Demais afirmações com evento marcado
      (`_precisa_marcado`), depois de zerar, por conexão separada, a marca dos eventos `v303%` que
      não são do 17 (os blocos anteriores deixam marcados, e a faixa conta todos): Superadmin e
      Comercial reais → `pode_ver: true`, `total: 1`, item só com `id`, `title`, `start_at` (sem
      dinheiro); 'Ver como' (`POST /api/auth/impersonate`, `auth.py:96`): Superadmin como FIGURINO
      não vê, como COMERCIAL vê; evento marcado com `cancelled_at` posto por UPDATE direto (a API
      recusa cancelar marcado desde a História 3) nunca é contado, e `GET /api/events/<id>` dele →
      `situacao == 'cancelado'`, `sumiu_do_google` e `google_html_link` nulos; resolvido por
      reaparecimento (`google.restaurar` + ciclo; a devolução é do cenário 10) → faixa vazia; dois
      marcados → os dois, na ordem de urgência (futuro antes de passado); e, por import tardio de
      `sumico_ops.faixa_sumidos(limite=1)` DENTRO do cenário (BLOQUEADO em `ImportError`), `total:
      2` e um item só, o mais urgente. _Cenários: escreve 17 (nasce vermelho e bloqueado)._ _Fonte:
      spec cenário 17; FR-009; R8; contrato §GET sumidos-google._
- [X] T027 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B4 (todos com
      `_precisa_marcado`), cenários 10a, 10 e 10b. O 10a roda com a trava ligada; só depois
      `app.config[<chave da trava>] = False`, dentro de `try/finally` que a devolve a `True` — nunca
      por variável de ambiente. 10a: `POST /api/events/<id>/devolver-ao-google` como Superadmin →
      409 `google_travado`; ZERO chamadas no dublê (nem `get`, nem `insert`, nem `patch`); marca e
      id intactos. 10: editar título e data do marcado e devolver → 200, `devolucao_google.resultado
      == 'recriado'`; UM `insert` com título, datas, local e descrição atuais, sem `attendees`;
      `google_event_id` novo; marca nula; `EventLog` com quem e quando; `AuditLog`
      `google_returned`; aviso lido; `GET /api/events/sumidos-google` deixa de contá-lo; venda,
      comprovantes, contrato e escala intactos; zero e-mail em `_emails` depois de
      `_esperar_threads()`; sem vaga fora do título, `source` não muda e o `EventLog` da devolução
      não traz a frase do elenco mantido pelo sistema. 10b: início e fim à meia-noite → corpo com
      `start.date` e `end.date`. _Cenários: escreve 10, 10a e 10b (nascem bloqueados)._ _Fonte: spec
      cenários 10, 10a, 10b; FR-012; FR-024; R13; R14._
- [X] T028 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B4, cenários
      10c a 10i (trava desligada em processo). 10c: `google.restaurar(id)` antes de devolver → zero
      `insert`, marca nula, `reapareceu`; variante editada enquanto marcada, com vaga criada fora do
      título → um `patch` no id velho com os dados do sistema e, depois de um ciclo, a vaga
      continua, sem e-mail de remoção. 10d: `insert` levanta → 502 `google_recusou`, mensagem fixa
      sem o erro bruto, marca e id intactos, `AuditLog` `google_return_failed`. 10e: consulta
      inconclusiva → 502 `google_inconclusivo`, um `get`, zero `insert`; variante com `RefreshError`
      no `.execute()` do `get` → 502 `google_desconectado`, zero `insert`, marca e id intactos. 10f:
      segundo POST → 409 `nao_marcado`, nenhum `insert` novo. 10g: vaga criada por `POST
      /api/events/<id>/roles` fora do título, devolver, ciclo → uma linha só com o id novo, a vaga
      continua, zero e-mail de remoção; por conexão separada, `source == 'platform'` e o `EventLog`
      da devolução termina com a frase fixa do elenco mantido pelo sistema. 10h: com ensaio-filho →
      um `insert`, `parent_event_id` intacto. 10i: não marcado (`nao_marcado`), cancelado
      (`cancelado`) e inexistente (404), cada um com o seu código afirmado → zero chamadas no dublê.
      Linha própria '10i (sem data)' (`_precisa_marcado`): evento marcado pelo ciclo e depois com
      `end_at` antes de `start_at` por UPDATE direto → 409 `sem_data`, zero chamadas no dublê (sem a
      marca, `_validar` responderia `nao_marcado` antes). _Cenários: escreve 10c a 10i (10i nasce
      vermelho; '10i (sem data)' e os demais, bloqueados)._ _Fonte: spec cenários 10c–10i; FR-012;
      FR-043; FR-044; R13; contrato §devolver-ao-google._
- [X] T029 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B4, cenários
      11 e 12. O 11 em duas linhas: '11 (Comercial recusado)' — Comercial REAL (o gate ignora o 'Ver
      como') faz `POST …/devolver-ao-google` → exatamente 403, nada muda, zero chamadas no dublê;
      '11 (Superadmin passa o gate)', sem `_precisa_marcado`: evento vazio NÃO marcado → 409
      `nao_marcado` na mesma rota (nunca 403), zero chamadas no dublê — o 200 do Superadmin é
      afirmado no cenário 10; assim o 11 não depende de marca e nasce vermelho inteiro. 12
      (`_precisa_marcado`), como Superadmin: `POST /api/events/<id>/cancelar` e `DELETE
      /api/events/<id>` → 409 com `codigo: 'sumiu_do_google'` e a mensagem do contrato; a rota
      antiga `POST /events/<id>/delete`, direto no backend (`routes.py:4318-4341`) → redireciona e o
      registro continua; o mesmo num satélite marcado sem mais nada. Em todos: registro, marca e
      aviso intactos, zero `delete` no dublê. Como Comercial: `POST …/solicitar-exclusao` → 200, a
      marca não muda e `GET /api/events/<id>` segue com `situacao == 'sumiu_do_google'`. Controle: o
      mesmo DELETE num evento vazio não marcado → 200. _Cenários: escreve 11 e 12 (nascem vermelho e
      bloqueados)._ _Fonte: spec cenários 11 e 12; FR-045; R16; spec §RBAC._
- [X] T030 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B5. Cenário 24
      (`_precisa_marcado`): três eventos marcados com o mesmo talento descartável — convite
      `pending`, futuro aceito e passado (marcado pelo 'Limpar eventos fantasma'). `GET
      /api/portal/agenda` → `em_confirmacao: true` em `pending_invites`, `upcoming` e `history`;
      `GET /api/portal/historico` → em `items`; nenhuma resposta traz a palavra 'Google'; `POST
      /api/portal/invites/<role_id>/accept` → 200. Outro talento descartável, de fora, não recebe
      nenhum dos três (deve falhar). Depois de devolvido (trava desligada em `app.config` num
      `try/finally` local que a devolve a `True`) → sem o aviso. Cenário 24b, sem depender de marca:
      evento que terminou há 2 dias (criado por `_evento_google` com fim há 2 dias: id `v303-…`,
      vaga de Coordenador nascida do sistema e preenchida por `_escalar` com o talento descartável —
      nunca `EventRole` por INSERT, CLAUDE.md §4; o mês não é liberado depois, então o ciclo não o
      toca) é avaliável; posto `cancelled_at`, sai de `rateable_event_ids` e `editable_event_ids`;
      `POST /api/portal/events/<id>/rate` → 400 'Este evento foi cancelado e não recebe avaliação.';
      nenhuma linha em `event_ratings`. _Cenários: escreve 24 (nasce bloqueado) e 24b (nasce
      vermelho)._ _Fonte: spec cenários 24 e 24b; FR-022; R19._
- [X] T031 `specs/303-sync-nao-apaga-venda/verify_303.py` — Em `verify_303.py`, bloco B9, cenário
      41, último do `finally`: depois de `_esperar_threads()` e de `limpar()`, afirmar por conexão
      separada zero resto — eventos `v303%`, talentos e usuários descartáveis, notificações e
      comissões deles, `audit_logs` do verify — e `calendar_sync_cache` igual ao guardado; afirmar
      `rede_bloqueada == []` (nenhuma chamada de rede escapou do dublê) e a trava de volta a `True`.
      Imprimir o resumo por bloco (por exemplo `B1 2/24 · B2 0/3, bloqueado por B1`), o total `N/N
      OK` e as contagens do dublê por verbo. `ruff check` e `ruff format` no arquivo (é novo).
      Registrar no docstring que o portão é a execução SEM argumentos. _Cenários: escreve 41 (verde
      desde a primeira execução)._ _Fonte: spec cenário 41; R18 (b, h); quickstart §3 e §5._
- [X] T032 Em `verify_303.py`, os argumentos `--semear-tela` e `--limpar-tela` (R18, item i), para a
      conferência de tela do quickstart §4. `--semear-tela` instala o dublê e o disjuntor de rede,
      passa pela guarda de ambiente e semeia e marca pelo caminho real — os futuros num mês isolado
      próprio (2031+), por `_ciclo()`; os passados em `MES_PASSADO`, por `_limpar_fantasmas` com o
      Superadmin descartável, porque o ciclo nunca lista mês passado (`sync.py:51-70`); cada mês
      liberado no dublê só durante a sua semeadura: dois eventos com venda, comprovante, contrato e
      talento descartável (um futuro, um passado); um satélite marcado e o seu principal; um marcado
      com exclusão solicitada; um de dia inteiro; e, para o portal, um talento descartável escalado
      em três marcados (convite pendente, futuro aceito, passado). Cria os usuários descartáveis
      Superadmin, Comercial e Figurino. Imprime ids, e-mails e o mês e sai SEM limpar (exit 0); as
      senhas são constante do próprio arquivo e não são impressas. `--limpar-tela` chama `limpar()`.
      Antes da História 1, `--semear-tela` sai dizendo que a marca ainda não existe. _Fonte: R18
      (i); quickstart §4._
- [X] T033 Rodar `verify_303.py` sem argumentos, ANTES de qualquer tarefa da História 1, com o
      backend local parado e as variáveis do quickstart §0, e gravar a saída inteira (stdout e
      stderr) em `specs/303-sync-nao-apaga-venda/verify_303_primeira_falha.txt` (precedente:
      `verify_299_primeira_falha.txt`). Conferir a lista fechada do plano: só podem estar OK o chão
      (0 e 41), o 18 (a trava nasce no Setup), o 15, '7 (apagado)' e '13 (a lista inteira falha)'; o
      11 nasce vermelho inteiro (a rota de devolver ainda não existe: 404 no lugar de 403). Cenário
      que depende de evento marcado sai BLOQUEADO, não FALHA de sintoma; nenhuma linha é erro de
      harness (`ImportError`, `AttributeError`, coluna inexistente). Qualquer outro OK é defeito do
      verify: corrigir e rodar de novo antes de seguir. Exit esperado: 1. _Fonte: plan §Constitution
      Check VIII; quickstart §3; Princípio VIII._
- [X] T034 [P] Em `specs/205-loja-interacoes-virtuais/verify_205.py`, bloco V7 (:781-814): (1) em
      :810, trocar a lista vazia por `outros_vivos` — `{'id': google_event_id}` de todo evento não
      VIRTUAL com `google_event_id` (molde `scripts/db/verify_cancelamento_evento.py:262-269`); hoje
      essa chamada apaga do espelho os eventos não virtuais do mês. (2) em volta da chamada, com
      `try/finally` local: `gcal_service.load_credentials = lambda: None` (cinto) e um espião em
      `gcal_service.consultar_evento` que guarda os ids consultados e repassa ao original; restaurar
      os dois. (3) o V7.2 passa a exigir três coisas: os virtuais sobrevivem; nenhum
      `google_event_id` virtual entre os consultados; a contagem de eventos não virtuais do mês
      igual antes e depois. Armadilha: o nome `consultar_original` já existe (:569, é da operadora).
      Rodar só depois da História 1. _Fonte: R18 (verify_205); spec §Portões além do verify;
      quickstart §3._

**Checkpoint**: coluna migrada no `manto_local`; consulta de três desfechos pronta; verify escrito e
rodado vermelho. Estado esperado da primeira execução (lista fechada — qualquer outro verde é defeito
do verify):

- **Verdes**: 0, 18, 41 (chão e trava), 15, "7 (apagado)", "13 (a lista inteira falha)".
- **Vermelhos**, pelo motivo certo: 1, 1b, 2b, 3, 4, 5, 6, "7 (auditoria)", 7a, 7b, 13 (as
  variantes de consulta), 13b, 13c, "14 (Sincronizar, não marcado)", 8, "17 (quem não vê)", 10i,
  o 11 inteiro, 24b.
- **Bloqueados** (dependem de evento marcado): 2, "14 (edição)", "14 (Sincronizar, marcado)", 9,
  13d, o resto do 17, 10, 10a a 10h, "10i (sem data)", 12, 24.

---

## Phase 3: História 1 — O evento com dinheiro que some do Google continua no sistema (P1) 🎯

**Objetivo**: a limpeza confere cada evento fora da lista no próprio Google; o vazio é apagado, o que
tem dinheiro fica e é marcado, com aviso no sino; a edição do marcado não escreve no Google; o
"Sincronizar" não altera evento que não está lá; a agenda e a tela do evento mostram a marca.

**Nesta fase** o desfecho "presente" da consulta só não apaga nem marca, e o "Sincronizar" de um
marcado que voltou sincroniza sem tirar a marca: aplicar a data nova e desmarcar são da História 5.

**Verificação da história (obrigatória)**: `verify_303.py --ate B1` com B0 e B1 inteiros em PASS
(0, 18; 1, 1b, 2, 2b, 3, 4, 5, 6, 7, 7a, 7b, 13, 13b, 13c, 14, 15); `verify_205.py` verde.

- [X] T035 [US1] Criar o módulo `app/calendar/sumico_ops.py`, núcleo puro (sem `flask.request` nem
      `current_user`), com docstring em pt-BR dizendo o porquê (a limpeza do sync apagava evento com
      dinheiro). Imports no topo: `db`, modelos, `now_sp`, `EVENT_TYPE_SHOW`, `notificacoes_ops` e
      `from app.calendar import service as gcal` — o Google é chamado SEMPRE por atributo
      (`gcal.consultar_evento`), para o dublê do verify e o espião do verify_205 interceptarem.
      Helpers de `app/calendar/routes.py` (`sync_events`, `_delete_event`, `_log_sync`,
      `_is_virtual_event`, `CALENDAR_ID`, `SOUND_TECH_*`) só por import tardio dentro das funções.
      Nesta tarefa: `filtro_marcados() -> ColumnElement[bool]` (`google_missing_since IS NOT NULL
      AND cancelled_at IS NULL`, fonte única de 'marcado') e o dataclass `ResultadoLimpeza` com as
      sete listas do contrato (`removidos: list[str]`; `marcados`, `movidos`, `desmarcados`,
      `presentes_fora_da_lista`, `inconclusivos`, `falhas: list[int]`), todas com
      `default_factory=list`. _Fonte: R1, R4; contrato §Núcleo; plan §Decisão de estrutura._
- [X] T036 [US1] `app/calendar/sumico_ops.py` — Em `sumico_ops.py`, criar `@dataclass(frozen=True)
      PresoAoEvento` (campos do contrato: `venda`, `recebido`, `n_comprovantes`, `tem_contrato`,
      `n_escalados`, `grupo`, `tecnico_automatico`), com `.vazio` e `.descricao()`, e
      `preso_ao_evento(event)`. Regras (R2): `venda` = `sale_value` ou 0; `recebido` =
      `cancel_ops.total_recebido` (reuso); `n_comprovantes` = contagem de `EventPayment`
      (existência, mesmo com valor nulo); `tem_contrato` = existe `EventContract`; `n_escalados` =
      `EventRole` com talento, MENOS — só em evento `SHOW` — a vaga `extra` `SOUND_TECH_CHARACTER`
      ocupada por `SOUND_TECH_TALENT_ID` (sempre, com ou sem cachê: decisão do dono — valor pago é
      evento realizado, que não some da agenda); comissão já paga NÃO segura o evento: apagado, ele
      gera o estorno contra o vendedor, como hoje (decisão do dono, 30/09); `grupo` = `satelite`
      (tem `group_leader_id`), `principal` (tem satélites) ou `None`; `tecnico_automatico` = SHOW
      com essa vaga intocada (o retrato diz 'só o técnico de som automático'). Dinheiro em
      `Decimal`; `.descricao()` no formato de data-model §Rastro, com `format_brl`. Armadilha: não
      chamar `pode_excluir` (`cancel_ops.py:57-74`), que dá 'não vazio' para todo SHOW. _Cenários:
      decide 3, 4, 5, 6, 7, 7a (passam a valer em T042)._ _Fonte: R2; FR-001; data-model §Estruturas
      em memória._
- [X] T037 [P] [US1] `app/notificacoes/notificacoes_ops.py` — Em `notificacoes_ops.py`: constante
      `KIND_EVENTO_SUMIU_GOOGLE` com o valor `evento.sumiu_google` no catálogo (depois de `:50`) e a
      entrada `(RoleName.COMERCIAL, RoleName.SUPERADMIN)` em `DESTINATARIOS_POR_KIND` (`:54-61`);
      produtor `notificar_evento_sumiu_google(event, *, marcado_em, preso) -> int` ao fim dos
      produtores (depois de `:290`), regime A, sem commit, via `emitir`: severidade `urgent`,
      entidade `(calendar_event, event.id)`, link `/events/<id>`, `dedupe_key` =
      `evento.sumiu_google:<id>:<marcado_em em %Y%m%d%H%M%S%f>`, título `Sumiu do Google Agenda —
      <título>`, corpo `dd/mm/aaaa · venda R$ X · recebido R$ Y · N pessoas escaladas` com as
      variantes do contrato §Sino (`sem data`, `sem venda`, `parte de grupo comercial`, `1 pessoa
      escalada`, `ninguém escalado`, `· contrato anexado`, `recebido R$ 0,00 (N comprovante(s) sem
      valor)`), dinheiro por `app.money.format_brl(valor, prefix=True)`. Armadilha: importar
      `PresoAoEvento` só sob `TYPE_CHECKING` (sumico_ops importa este módulo); atualizar a docstring
      `:8-11`, que declara os imports do módulo. _Cenários: 2 (texto e unicidade do aviso; passa a
      valer em T042)._ _Fonte: R7; FR-010; contrato §Sino; data-model §notifications._
- [X] T038 [US1] `app/calendar/sumico_ops.py` — Em `sumico_ops.py`, criar `marcar(event, preso, *,
      contexto: str) -> datetime | None` (R6). `carimbo = now_sp()`; `UPDATE` condicional em
      `calendar_events` gravando `google_missing_since = carimbo` com `WHERE id = :id AND
      google_missing_since IS NULL AND cancelled_at IS NULL`; `rowcount` zero → devolve `None`, sem
      histórico, auditoria nem aviso (outro processo marcou). Quem pega a linha:
      `db.session.refresh(event)`; `n = notificacoes_ops.notificar_evento_sumiu_google(event,
      marcado_em=carimbo, preso=preso)`; `EventLog` (ator e papel `Sistema`, SEM `created_at` — vale
      o default UTC, que `agenda_read.py:210-214` converte) com `Sumiu do Google Agenda — mantido no
      sistema. Preso: <preso.descricao()>. Aviso enviado a N pessoa(s).`; `_log_sync` com a ação
      `sumiu_do_google`, o retrato e o `contexto`. NÃO comita. Armadilhas: o produtor roda ANTES do
      `EventLog` (o texto leva N) e recebe o `carimbo` local, nunca uma releitura do objeto; o
      parâmetro `avisar` não existe. _Cenários: 1, 2, 2b (passam a valer em T042)._ _Fonte: R6, R7;
      FR-004, FR-010, FR-023; data-model §Rastro._
- [X] T039 [US1] `app/calendar/routes.py` — Em `routes.py::_delete_event` (`:305-338`): antes de
      `_clear_event_side_tables(event.id)` (`:320`), chamar `_clear_event_side_tables(ensaio.id)`
      para cada `event.ensaios` — os ensaios saem por cascade do ORM (`models.py:352-357`) sem
      passar por essa limpeza, e o `EventLog` do ensaio (FK sem cascade, `models.py:575`) estoura a
      exclusão do pai, a cada ciclo; e, antes de `db.session.delete(event)` (`:337`), chamar
      `notificacoes_ops.apagar_por_entidade` para `(calendar_event, event.id)`, por import tardio,
      para o aviso do sino não ficar com link morto. Vale para TODA exclusão (a limpeza do sync e o
      Excluir da 224): atualizar a docstring e comentar o porquê. Não mexer em gate, regra de vazio,
      recusa do líder de grupo nem na remoção no Google; o ensaio não é removido do Google (dívida
      do docs/05). _Cenários: 7b (variante DELETE /api/events/<id>; a variante do sync passa em
      T042)._ _Fonte: R4, R7; FR-007; spec §Casos de borda (evento vazio com ensaio ligado); plan
      §Constitution Check IV._
- [X] T040 [US1] `app/calendar/sumico_ops.py` — Em `sumico_ops.py`, criar `_decidir_candidato`
      (decide UM evento; não comita). Ordem (R4): (1) venda virtual (`_is_virtual_event`) →
      `_log_sync` de `virtual_divergente` com o texto de hoje (`routes.py:377-381`), sem consulta;
      (2) já marcado (`event.is_google_missing`) → pula, sem consulta; (3) disjuntor aberto →
      inconclusivo, sem consulta; (4) `gcal.consultar_evento(CALENDAR_ID, event.google_event_id)`:
      inconclusivo → nada, devolvendo o `motivo` a quem chama; presente → NESTA fase só não apaga
      nem marca (aplicar data nova e `mesmos_dados` são da História 5); ausente → `preso =
      preso_ao_evento(event)`: vazio → `_log_sync` de `auto_deleted` com o que o Google respondeu
      (`http_404`, `http_410` ou `cancelled`) mais `preso.descricao()`, e `_delete_event(event)`;
      com dinheiro → `marcar(event, preso, contexto=<AAAA-MM>)` (retorno `None` não é marca nem
      falha). Devolve o desfecho para `limpar_mes` registrar depois do commit. _Cenários: 1, 2, 2b,
      3, 4, 5, 6, 7, 7a, 15 (passam a valer em T042)._ _Fonte: R2, R3, R4; FR-001, FR-002, FR-003,
      FR-007, FR-023; data-model §Rastro (auto_deleted)._
- [X] T041 [US1] `app/calendar/sumico_ops.py` — Em `sumico_ops.py`, criar `limpar_mes(items, year,
      month) -> ResultadoLimpeza` (sem `simular` nem `avisar`). Candidatos = a consulta de hoje
      (`routes.py:348-368`: `google_event_id` preenchido, `cancelled_at` nulo, `start_at` dentro do
      mês) cujo id não veio na lista. Materializar os IDS antes do laço; por id:
      `db.session.get(CalendarEvent, id)` (`None` = já saiu por cascade ou por outro processo →
      segue, não é falha); `try` → `_decidir_candidato` → `db.session.commit()` (todo ramo comita,
      inclusive o virtual); `except Exception` → `rollback`, `logger.exception` com o id, id em
      `falhas`, segue. Registrar em `ResultadoLimpeza` só DEPOIS do commit (título lido antes do
      delete). Disjuntor = variável local da chamada: o primeiro inconclusivo de motivo `rede`,
      `http_5xx` ou `sem_credencial` faz os candidatos restantes saírem como `inconclusivos` sem
      consulta; `http_403`, `http_429`, `http_4xx` e `sem_inicio` não abrem. Funções de até ~30
      linhas e 3 níveis. _Cenários: 13, 13b, 7b (passam a valer em T042)._ _Fonte: R4; FR-003,
      FR-040; contrato §Núcleo._
- [X] T042 [US1] `app/calendar/routes.py` — Em `routes.py::_cleanup_stale_events` (`:341-390`):
      manter o nome e a entrada `(items, year, month)`; trocar o corpo inteiro por `return
      sumico_ops.limpar_mes(items, year, month)` (import tardio de `app.calendar.sumico_ops`); o
      retorno passa de `list[str]` para `ResultadoLimpeza`. Reescrever a docstring dizendo o que
      acontece de fato (FR-025): cada evento fora da lista é conferido no Google; vazio é removido;
      com dinheiro fica e é marcado; mudança de data não é sumiço; na dúvida, o evento fica. Não
      mover nem renomear nada. O chamador Jinja `/agenda?force_sync=1` (`:475`) ignora o retorno:
      zero linha alterada ali. Os dois consumidores do retorno (`sync.py:79`,
      `admin_config_write.py:104`) ficam quebrados até T043 e T045 — fazer as três em sequência, sem
      rodar o ciclo no meio. _Cenários: 1, 2, 2b, 3, 4, 5, 6, 7, 7a, 7b, 13, 13b, 15 — pelo ciclo,
      só depois de T043._ _Fonte: R4; FR-001, FR-025; contrato §Núcleo; plan §Resumo._
- [X] T043 [US1] `app/calendar/sync.py` — Em `sync.py::run_calendar_sync`: em `:79-82`, guardar o
      `ResultadoLimpeza` (hoje `len(...)` de uma lista); resumo do mês com os números diferentes de
      zero (removidos, marcados, com data nova, de volta ao Google, sem confirmação, com falha);
      `errors += 1` quando `resultado.falhas` não está vazio — o mês continua sendo carimbado por
      `_mark_month_synced`; inconclusivo NÃO conta como erro. Acumular os totais do ciclo e, em
      `:97-102`, escrevê-los no `detail` ANTES de `' | '.join(results[:8])` (a lista de meses é
      cortada nos oito primeiros), com a frase fixa do contrato, sempre presente: `Sumiços: M
      marcado(s), D com data atualizada, V de volta ao Google Agenda, I sem confirmação, F com
      falha.` (FR-042). `movidos` e `desmarcados` ficam zero até a História 5, que também soma a
      reconferência. Atualizar a docstring do módulo (`:7-8`) se o fluxo descrito mudar. _Cenários:
      13 (no `detail` do `AuditLog` do ciclo, a frase `Sumiços:` com `0 com falha` e ao menos `1 sem
      confirmação`), 13b (variante pelo ciclo: `1 com falha`); o status `sync_ok`/`sync_erro` nunca
      é afirmado — todo ciclo do verify sai `sync_erro`._ _Fonte: FR-042; R4; data-model §Rastro
      (resumo do ciclo)._
- [X] T044 [US1] `app/calendar/sync.py` — Em `sync.py`, no `except Exception as exc` do mês
      (`:83-85`): chamar `db.session.rollback()` SÓ quando `isinstance(exc, SQLAlchemyError)`
      (import de `sqlalchemy.exc`), antes de registrar o erro do mês. Comentário com o porquê:
      depois de um erro de banco a sessão fica inválida e todos os meses seguintes falham (defeito
      de hoje); em erro que NÃO é de banco o pendente de `sync_events` tem de seguir na sessão — os
      e-mails já saíram (`routes.py:2277`, `:2341`, `:2391`) e um rollback desfaria a vaga apagada e
      o carimbo `event_changed_at`, repetindo o e-mail a cada ciclo. Não tocar o `except` do log
      final (`:116-117`). 'Marca sem aviso' não depende deste rollback: a unidade de trabalho da
      limpeza é o evento (T041). _Cenários: 13c._ _Fonte: research §Riscos; plan §Rastreamento de
      complexidade (IV); R4._
- [X] T045 [US1] `app/api/admin_config_write.py` — Em `admin_config_write.py`, ação `cleanup_past`
      (`:92-117`): ler o `ResultadoLimpeza` devolvido por `_cleanup_stale_events` (`:104`) e
      devolver, por mês, `removed`, `marcados`, `movidos`, `desmarcados`, `inconclusivos` e `falhas`
      (números), com `ok` falso quando há falha; trocar a `message` (`:112-116`) pelo texto fixo do
      contrato: `Limpeza concluída em M mês(es): R removido(s), K mantido(s) e marcado(s), D com
      data atualizada, V de volta ao Google Agenda, I sem confirmação do Google, F com falha.`
      (somas de todos os meses); quando algum mês não pôde ser consultado (`ok` falso com `err`), a
      mensagem termina com ` E mês(es) com erro.` `sync_now` (`:64-90`) não muda; RBAC inalterado
      (`_require_superadmin`, já no início da view, `:52-54`). A view só soma e serializa — nenhuma
      regra de negócio aqui. _Cenários: 1b._ _Fonte: FR-042; contrato §Endpoints alterados e §Textos
      fixos._
- [X] T046 [US1] `app/api/admin_config_write.py` — Em `admin_config_write.py`, no `except Exception
      as exc` do mês de `cleanup_past` (`:107-108`): `db.session.rollback()` só quando a exceção é
      `SQLAlchemyError`, antes de registrar `ok: False` e `err` — mesma regra e mesmo comentário de
      T044 (erro de banco invalida a sessão e derruba os meses seguintes; em erro que não é de banco
      o pendente de `sync_events` tem de sobreviver, porque os e-mails já saíram). O módulo hoje não
      importa `db`: acrescentar `from app import db` e o import de `sqlalchemy.exc`. O `except` de
      `sync_now` (`:80-81`) NÃO é tocado — os documentos pedem o rollback só no ciclo e no 'Limpar
      eventos fantasma'. _Cenários: 13c (variante do Limpar)._ _Fonte: research §Riscos; plan
      §Rastreamento de complexidade (IV)._
- [X] T047 [P] [US1] `app/calendar/event_ops.py` — Em `event_ops.py::_sincronizar_e_trocar_tipo`,
      condição do push (`:638`): passar a `if changed_core and event.google_event_id and not
      event.is_google_missing:`. Evento marcado não tem par no Google: sem a condição, cada
      salvamento falharia com aviso e a troca que entra ou sai de SHOW seria desfeita com
      `EventTypeChangeBlocked` (`:649-659`). Com ela, `google_ok` segue verdadeiro: salva com 200,
      sem a frase de falha em `warnings`, a automação da troca de tipo roda e a marca não é tocada.
      Atualizar a docstring (`:608-636`) com o caso do marcado e comentar o porquê. É o ÚNICO ponto:
      `update_event_core` (`:984`) e `update_event_basics` (`:1071`) herdam; não tocar
      `update_ensaio` (`:1683`) nem `edit_ensaio` (`routes.py:2652`) — ensaio nunca é marcado.
      _Cenários: 14 (edição e troca de tipo)._ _Fonte: R11; FR-008; contrato §Endpoints alterados
      (PATCH)._
- [X] T048 [US1] `app/calendar/routes.py` — Em `routes.py::_sync_single_event_flow` (`:4191-4208`):
      trocar `fetch_single_event` (`:4203`) por `gcal.consultar_evento(CALENDAR_ID,
      event.google_event_id)` (import tardio `from app.calendar import service as gcal`, chamada por
      atributo). Desfechos: ausente → devolve o status novo `ausente_no_google` sem tocar nada (nem
      evento, nem escala; não apaga nem marca); inconclusivo → `not_found`, como hoje; presente →
      `sync_events([consulta.item])`, commit, `ok`. Atualizar a docstring com o status novo. Remover
      `fetch_single_event` do import do topo (`:24`), que fica sem uso (ruff F401);
      `service.fetch_single_event` em si NÃO muda (o Meet da Loja Virtual depende dela,
      `virtuais_ops.py:1679`). A retirada da marca no ramo presente (`desmarcar` antes do
      `sync_events`) entra na História 5. _Cenários: 14 (Sincronizar; completa com T050)._ _Fonte:
      R11, R3; FR-039; SC-005._
- [X] T049 [US1] `app/calendar/routes.py` — Em `routes.py::sync_single_event` (wrapper Jinja vivo do
      Sincronizar, `:4237-4250`): acrescentar, entre o `elif` de `not_found` (`:4246-4247`) e o
      `else` (`:4248`), um `elif` para o status `ausente_no_google` com `flash` de erro `Este evento
      não está mais no Google Agenda. Nada foi alterado.`. Sem ele o status novo cairia no `else` e
      a rota antiga diria `Evento sincronizado com sucesso`. Só esse `elif`: nenhum Jinja novo, nada
      movido nem renomeado. _Fonte: R11; FR-039; plan §Código (routes.py, 6 toques)._
- [X] T050 [P] [US1] `app/api/agenda_write.py` — Em `agenda_write.py::api_sync_event` (`:621-636`):
      depois do teste de `no_google_id` (`:632-633`), tratar o status `ausente_no_google` com
      `json_error` 409 e a mensagem fixa `Este evento não está mais no Google Agenda. Nada foi
      alterado.` — para qualquer evento, marcado ou não. `not_found` segue 502 (`:634-635`) e `ok`
      segue devolvendo o detalhe (`:636`). O endpoint continua SEM gate de papel (declarado em spec
      §RBAC); atualizar a docstring dizendo que ele confere o evento antes de mexer. A view só
      traduz o status do núcleo. _Cenários: 14 (Sincronizar de evento marcado e não marcado,
      ausentes; resposta completa e mínima)._ _Fonte: R11; FR-039; contrato §Endpoints alterados
      (POST /sync)._
- [X] T051 [US1] `app/api/agenda_read.py` — Em `agenda_read.py::serialize_event_summary` (`:70-89`):
      acrescentar ao dict `situacao` (de `event.situacao`) e `situacao_desde` (ISO de
      `event.situacao_desde`, ou `None`). É o serializador único do mês (`build_agenda_month`,
      `:131-132`), do dia e da busca (`app/api/agenda.py:65` e `:92`): um ponto cobre as três
      leituras. Sem dinheiro, sem motivo, sem autor — o resumo vai a todo papel que vê a agenda,
      inclusive o revendedor EducaManto; atualizar a docstring. A precedência cancelado >
      sumiu_do_google > exclusao_solicitada vem pronta da propriedade do modelo: não recombinar
      colunas aqui. _Fonte: R10; FR-033 (parte), FR-004; contrato §Endpoints alterados (GET
      /api/agenda, day, search)._
- [X] T052 [US1] `app/api/agenda_read.py` — Em `agenda_read.py::serialize_event_detail`, bloco
      `event` (`:701-749`): acrescentar `situacao` (de `event.situacao`) e `sumiu_do_google` =
      objeto com `desde` (ISO de `google_missing_since`) quando `event.is_google_missing`, senão
      `None` — não nulo só quando marcado E não cancelado; e trocar `:707` para mandar
      `google_html_link` nulo quando o evento está marcado ou cancelado (hoje
      `event.google_html_link or None`). O link nulo no servidor também esconde 'Editar no Google
      Agenda' no bundle antigo durante a janela de deploy. Fica antes do retorno antecipado do
      ENSAIO (`:762-765`); nenhuma flag nova em `_role_flags` (`:149-198`) nesta fase; comentar o
      porquê. _Fonte: R10, R11; FR-004, FR-033 (parte); contrato §Endpoints alterados (GET
      /api/events/<id>)._
- [X] T053 [P] [US1] `frontend/apps/internal/src/lib/agenda.ts` — Em `lib/agenda.ts`: criar o ÚNICO
      `export type SituacaoEvento` com os literais `cancelado`, `sumiu_do_google` e
      `exclusao_solicitada`; em `EventoResumo` (`:7-18`) acrescentar `situacao?: SituacaoEvento |
      null` e `situacao_desde?: string | null` (`EventoBusca`, `:58-61`, herda); em
      `EventoDetalhe.event` (`:291-348`) acrescentar `situacao?: SituacaoEvento | null` e
      `sumiu_do_google?: { desde: string } | null`. Todos OPCIONAIS (backend e bundle sobem no mesmo
      push, em ordem não garantida): toda tela trata campo ausente como 'sem situação'.
      `google_html_link` já é `string | null` (`:346`) — sem mudança. `devolucao_google?` é da
      História 3. _Fonte: R10; contrato §Endpoints alterados e nota do `type SituacaoEvento`._
- [X] T054 [P] [US1] `frontend/apps/internal/src/components/SeloSituacao.tsx` — Criar
      `components/SeloSituacao.tsx`, exportando `SeloSituacao`: o selo único da situação, sobre o
      `Badge` de `@manto/ui` (tom `gold`). Nesta entrega só desenha quando a situação é
      `sumiu_do_google` (o selo do cancelado é da terceira entrega); qualquer outro valor, ou
      ausência, devolve `null`. Props: `situacao`, `desde`, `compacto`. Completo: ícone `CalendarX`
      (o mesmo do aviso do sino) + texto `Sumiu do Google`, com `title` `Sumiu do Google Agenda —
      percebido em dd/mm/aaaa`. Compacto (chip do Mês, bloco curto do Dia): só o ícone, com
      `aria-label` `Sumiu do Google Agenda`. Armadilhas: `Badge` não aceita `title`
      (`packages/ui/src/components/badge.tsx:6-10`) — o tooltip vai num `span` em volta; a data sai
      por `formatShortDate` de `@manto/ui` (fonte única, dd/mm/aaaa; nunca `toISOString()`); o
      componente exportado precisa de nome diferente do tipo `SituacaoEvento`. Não entra em
      `@manto/ui`; sem CSS solto nem `style` inline. _Fonte: R10; FR-004; contrato §Textos fixos
      (Selo na agenda)._
- [X] T055 [P] [US1] `frontend/apps/internal/src/components/AgendaListView.tsx` — Em
      `AgendaListView.tsx::AgendaListItem` (`:25-71`): renderizar o selo completo (com
      `event.situacao` e `event.situacao_desde`) logo depois do selo de categoria (`:52-56`) e FORA
      do `span` do título (`:57-60`), que também contém o subtítulo da cliente usado na busca. A
      busca (`AgendaSearchResults.tsx:26`) reusa este item e herda o selo sem mudança de código. Sem
      situação, a linha fica idêntica à de hoje. _Fonte: R10 (Lista e busca); FR-004._
- [X] T056 [P] [US1] `frontend/apps/internal/src/components/CalendarGrid.tsx` — Em
      `CalendarGrid.tsx`, chip do evento (`:109-122`): quando a situação é `sumiu_do_google`, o
      ícone do selo (modo compacto, `aria-label` `Sumiu do Google Agenda`) entra ANTES do horário
      (`:119`); o chip mantém a cor da categoria (`:117`); e o `title` (`:115`) vira `<título> —
      Sumiu do Google Agenda, percebido em dd/mm/aaaa` (de `situacao_desde`, por `formatShortDate`
      de `@manto/ui`). O texto do selo não cabe no chip (~80 px, `truncate`). Marcado escondido no
      `+N` (`:124-135`) só mostra o ícone ao expandir o dia — aceito, a faixa lista todos. Não mudar
      a ordenação nem `MAX_VISIBLE_PER_DAY` (`:14`). _Fonte: R10 (Mês); FR-004; contrato §Textos
      fixos._
- [X] T057 [P] [US1] `frontend/apps/internal/src/components/DayTimelineView.tsx` — Em
      `DayTimelineView.tsx`: a lista 'Sem horário' (`:73-86`) e o bloco detalhado (`detailed`,
      `:119`, `:136`) ganham o selo completo; no bloco curto, só o ícone antes do título (`:137`), e
      o `title` do bloco (`:124-126`) ganha o texto `Sumiu do Google Agenda — percebido em
      dd/mm/aaaa`. A visão Dia não filtra cancelado (`app/api/agenda.py:85-90`): a marca nunca
      aparece em evento cancelado porque o servidor manda a situação `cancelado` — não recombinar
      campos na tela. O chip e o bloco já são `Link`: nada de botão nem `InfoTip` dentro deles; em
      toque, a data é lida no banner do evento. _Fonte: R10 (Dia); FR-004, FR-033 (parte)._
- [X] T058 [P] [US1] `frontend/apps/internal/src/components/notificacoes/NotificacaoItem.tsx` — Em
      `NotificacaoItem.tsx`: acrescentar a entrada `evento.sumiu_google` → `CalendarX` em
      `ICONE_POR_KIND` (`:7-11`; import em `:1`). Para aviso `urgent` (todos, não só o novo), trocar
      o `truncate` do título (`:53`) por `line-clamp-2` e o do corpo (`:58`) por `line-clamp-3`, com
      o texto inteiro no atributo `title` de cada um; aviso `info` continua com `truncate`. Com duas
      linhas, a linha do título (`flex items-center`, `:49`) precisa alinhar o ponto de não lida ao
      topo. Atualizar o comentário do componente (`:22-24`). Porquê: com o prefixo fixo `Sumiu do
      Google Agenda — ` sobram ~10 caracteres para o nome do evento no painel de 375 px. _Fonte: R7
      (Na tela); FR-010; contrato §Sino._
- [X] T059 [US1] `frontend/apps/internal/src/components/EventDetail/EventHeader.tsx` — Em
      `EventHeader.tsx`, menu (`:235-238`): mostrar o item Sincronizar por `(event.google_html_link
      || event.sumiu_do_google) && canCasting` — o servidor passa a mandar o link nulo no evento
      marcado, e sem isto o botão sumiria junto (a spec quer o Sincronizar presente, respondendo que
      o evento não está no Google). 'Editar no Google Agenda' (`:243-248`) continua só com
      `google_html_link`: sem mudança de código. O 409 do servidor aparece pela linha que já existe
      (`:411`, `sync.error?.message`). O banner é montado em tarefa própria, logo adiante;
      desabilitar 'Excluir ou cancelar' (`:306-312`) e 'Analisar e decidir' (`:390-392`) é da
      História 3. _Fonte: R11; FR-039; spec §Casos de borda (botão Sincronizar do evento marcado)._
- [X] T060 [US1] Crie `frontend/apps/internal/src/components/EventDetail/SumiuDoGoogleBanner.tsx`,
      exportando `SumiuDoGoogleBanner({ data, onDevolver })` (`onDevolver` opcional: o botão só
      chega na História 3); renderiza só quando `data.event.sumiu_do_google` existe. Para todos que
      abrem o evento: as duas frases fixas do contrato (§Textos fixos, "Banner, para todos"), com o
      `dd/mm/aaaa` de `sumiu_do_google.desde` — sem dinheiro, sem botão, sem motivo. Para quem tem
      `flags.can_request_delete && !flags.can_delete`: a frase fixa do Comercial. O front não decide
      por papel, só por flag (`flags` é `Record<string, boolean>`: chave ausente = falso). Molde
      visual: o banner "Exclusão solicitada" (`EventHeader.tsx:379`). Ocupa a largura do conteúdo,
      sem rolagem horizontal em 375 px, sem `style` inline e sem `sticky`. _Fonte: R15; FR-004;
      FR-011; contrato §Textos fixos._
- [X] T061 [US1] Em `frontend/apps/internal/src/components/EventDetail/EventHeader.tsx`, montar
      `<SumiuDoGoogleBanner data={data} />` entre o banner de cancelado (`:364-376`) e o de exclusão
      solicitada (`:378`) — o do sumiço vem primeiro quando os dois existem. Nesta fase o banner só
      tem a parte comum (a marca, "percebido em", a frase da edição e, para o Comercial, a frase
      dele): é o aceite 4 da História 1. O quadro, o botão e o diálogo chegam na História 3.
      Localizar pelo conteúdo: as linhas terão andado com a tarefa do menu. _Fonte: FR-004; História
      1, aceite 4; R15._
- [X] T062 [P] [US1] `frontend/apps/internal/src/lib/adminConfig.ts` — Em `lib/adminConfig.ts`: em
      `SyncRunResult.results[]` (`:126-129`) acrescentar, OPCIONAIS, `marcados?`, `movidos?`,
      `desmarcados?`, `inconclusivos?` e `falhas?` (números). Em `useRunSync` (`:131-143`), no
      `onSuccess`, chamar também `invalidarNotificacoes(queryClient)` (`lib/notificacoes.ts:54-56`):
      a limpeza cria avisos no sino e o badge esperaria o poll de 60 s. A invalidação da faixa
      (`invalidarSumidosGoogle`) entra na História 2, quando `lib/sumidosGoogle.ts` existir. _Fonte:
      FR-042; contrato §Endpoints alterados (admin/sync/run) e §Frontend — hooks._
- [X] T063 [P] [US1] `frontend/apps/internal/src/pages/AdminSyncPage.tsx` — Em `AdminSyncPage.tsx`:
      trocar o `window.confirm` (`:25`) por `ConfirmDialog` de `@manto/ui` — título `Limpar eventos
      fantasma?`, o texto fixo do contrato (§Textos fixos, confirmação do `/admin/sync`), botão
      `Limpar`, `pending` de `runSync.isPending`, erro dentro do diálogo; fecha no sucesso.
      Resultado (`:34-38`): abaixo da `message`, uma linha por mês de `results[]` que tenha algum
      número diferente de zero (removidos, marcados, com data atualizada, de volta ao Google, sem
      confirmação, com falha); o mês com `ok` falso por erro de consulta aparece como `AAAA-MM: não
      foi possível consultar o Google Agenda`; quando a soma de `falhas` ou de `inconclusivos` é
      maior que zero, ou há mês com erro, a caixa usa o tom de alerta (`bg-gold-soft text-gold-ink`)
      em vez do de sucesso. `sync_now` usa a mesma caixa e não traz esses campos: tratar ausente
      como zero. _Fonte: FR-042, FR-025 (parte); contrato §Textos fixos (/admin/sync); Princípio V._
- [X] T064 [US1] `specs/303-sync-nao-apaga-venda/verify_303.py` — Checkpoint da História 1 (não
      edita código). Com o ambiente do quickstart §0 e o backend local PARADO: rodar `verify_303.py
      --ate B1` e conferir o resultado contra a lista de verdes e vermelhos desta fase; rodar
      `specs/205-loja-interacoes-virtuais/verify_205.py` (V7.1 e V7.2 verdes, nenhum id virtual
      entre os ids consultados, contagem de eventos não virtuais do mês igual antes e depois); `cd
      frontend && npm run typecheck`; `ruff check` nos arquivos Python tocados e `ruff format` só em
      `app/calendar/sumico_ops.py`. Não rodar os verifies antigos de `scripts/db/` (`verify_151`
      consultaria o Google real; `verify_168` quebra no `cleanup_past`). Verde fora da lista
      esperada é defeito do verify, não progresso. _Cenários: 1, 1b, 2, 2b, 3, 4, 5, 6, 7, 7a, 7b,
      13, 13b, 13c, 14, 15._ _Fonte: spec §Verificação (portões além do verify); quickstart §3 e §5;
      Princípio VIII._

**Checkpoint**: nenhum evento com dinheiro é apagado pelo sync. Na execução sem argumentos ainda
ficam vermelhos 8, 9, 13d, 17, 10 a 10i, 11, 12, 24 e 24b.

---

## Phase 4: História 5 — Evento que só mudou de data não vira sumiço (P2)

**Objetivo**: o evento presente no Google com outra data chega à data nova no mesmo registro; o
marcado que reaparece perde a marca sozinho (vale o Google); o que some de novo avisa de novo.

**Verificação da história (obrigatória)**: `verify_303.py --ate B2` com B0 a B2 em PASS (8, 9, 13d).

- [X] T065 [US5] Em app/calendar/sumico_ops.py (nasce na História 1), criar `desmarcar(event, *,
      motivo: str, actor_name: str = "Sistema", actor_role: str = "Sistema") -> bool`, a única
      função que retira a marca. Não marcado (`is_google_missing` falso): devolve False sem
      escrever. Marcado: guardar o carimbo antigo, zerar `google_missing_since`, chamar
      `notificacoes_ops.marcar_lidas_por_entidade("calendar_event", event.id,
      KIND_EVENTO_SUMIU_GOOGLE)` (app/notificacoes/notificacoes_ops.py:362) e gravar o rastro
      "Reaparecer": `EventLog` `Reapareceu no Google Agenda — a marca "Sumiu do Google Agenda" de
      dd/mm/aaaa foi retirada.` com o ator recebido, e `_log_sync("google_reapareceu", …)`
      (routes.py:393, import tardio). NÃO comita. Armadilhas: `EventLog` sem `created_at` (default
      UTC, models.py:579; a tela converte); cortar `actor_role[:60]` (models.py:577 e :594).
      `motivo` é fechado — `MOTIVO_REAPARECEU` ou `MOTIVO_DEVOLVIDO`, constantes do módulo: o rastro
      acima só é gravado no reaparecimento; na devolução (História 3) a função só zera a coluna e
      marca o aviso como lido — o rastro é o da própria devolução. _Fonte: R12, R7, R1; FR-006,
      FR-010, FR-023; data-model §Invariantes e §Rastro._
- [X] T066 [US5] Em app/calendar/sumico_ops.py, criar `mesmos_dados(event: CalendarEvent, item:
      dict) -> bool`: compara título, início, fim, local e descrição do item do Google com o banco
      PELOS VALORES QUE `sync_events` GRAVARIA, não pelo item cru. Título:
      `_strip_reserved_title_segments(item.get("summary") or "Sem título")` (routes.py:1935; uso em
      :2229-2233; import tardio). Início e fim: `gcal.parse_event_datetime(item)`
      (service.py:194-214 — naive São Paulo; dia inteiro = meia-noite, com o fim exclusivo do
      Google). Local e descrição: nulo = vazio, sem espaços nas pontas (o sync grava o valor cru,
      routes.py:2234-2235). Função única, reusada pela devolução (R13). Escrever no docstring o
      invariante: logo depois de `sync_events([item])`, `mesmos_dados` do mesmo item é True — sem
      isso, "+ Coordenador" no título do Google daria "mudou" a cada ciclo. _Fonte: R5 (Como
      comparar); FR-041; contrato §Núcleo._
- [X] T067 [US5] Em `_decidir_candidato` (app/calendar/sumico_ops.py), preencher o desfecho
      `presente`, que a História 1 deixa sem ação. Se `not mesmos_dados(event, consulta.item)`:
      chamar `sync_events([consulta.item])` (routes.py:2184, import tardio — acha pelo id em :2247,
      grava em :2291-2295, avisa o elenco aceito em :2340-2342 e comita sozinho em :2406 e :2434) e
      pôr o id em `resultado.movidos`. Se iguais: não chamar nada, pôr o id em
      `presentes_fora_da_lista` e gravar `_log_sync("presente_fora_da_lista", event, details=…)` só
      se ainda não houver linha dessa ação para o evento no dia (`AuditLog` por
      `entity_type="agenda"`, `entity_id`, `action` e `created_at`, que é UTC — models.py:600), com
      `serie_recorrente` no detalhe quando `consulta.motivo` trouxer. Nunca marcar, apagar nem
      avisar no sino. Usar o id materializado: o commit de `sync_events` expira o objeto. _Cenários:
      8._ _Fonte: R5, R4; FR-002, FR-041; data-model §Rastro._
- [X] T068 [US5] Em `limpar_mes` (app/calendar/sumico_ops.py), antes do laço dos candidatos,
      desmarcar o evento marcado cujo id voltou à lista do mês: materializar os ids com
      `filtro_marcados()` e `google_event_id` em `live_ids`, SEM filtro de `start_at` — o filtro de
      mês dos candidatos (hoje routes.py:364-365) não serve aqui: o evento que atravessa a virada
      vem na lista de um mês com início no outro. Por id: reler com `db.session.get`,
      `desmarcar(event, motivo=MOTIVO_REAPARECEU)` com ator Sistema, commit, id em
      `resultado.desmarcados`; exceção → rollback, log, id em `falhas`. Não consultar o Google nem
      chamar `sync_events`: a lista (`showDeleted=False`, service.py:154) já confirma a presença, e
      os três chamadores rodam `sync_events(items)` antes da limpeza (sync.py:78-79,
      admin_config_write.py:103-104, routes.py:474-475), então os dados do Google já estão gravados.
      _Cenários: 9._ _Fonte: R12, R4; FR-006, FR-042._
- [X] T069 [US5] Em app/calendar/sumico_ops.py, criar `reconferir_marcados() -> dict[str,
      list[int]]` com as chaves `reapareceram`, `seguem_ausentes`, `inconclusivos`, `falhas`.
      Materializar os ids de `filtro_marcados()`; por id, reler com `db.session.get` (None ou já sem
      marca = segue) e chamar `gcal.consultar_evento(CALENDAR_ID, event.google_event_id)` sempre por
      atributo do módulo. Presente → `desmarcar(event, motivo=MOTIVO_REAPARECEU)` +
      `sync_events([item])` (um commit só, o do próprio sync — vale o Google); ausente e
      inconclusivo → nada: aqui "ausente" é no-op, nunca apaga nem marca. Disjuntor LOCAL da
      chamada: o primeiro inconclusivo de motivo `rede`, `http_5xx` ou `sem_credencial` encerra as
      consultas e os restantes saem como inconclusivos; `http_403`, `http_429`, `http_4xx` e
      `sem_inicio` não abrem. Cada evento em try/except próprio: `rollback`, `logger.exception`, id
      em `falhas`, e segue. _Fonte: R12, R4, R3; FR-006, FR-040._
- [X] T070 [P] [US5] Em `run_calendar_sync` (app/calendar/sync.py), chamar
      `sumico_ops.reconferir_marcados()` antes do laço de meses — depois de `results` (linha 73) e
      antes do `for m in months` (linha 74) —, com import tardio junto dos da linha 43-49. Envolver
      em try/except próprio: exceção → `db.session.rollback()`, registrar e seguir; falha na
      reconferência nunca impede os meses de listar, sincronizar e limpar (cada mês tem o seu
      disjuntor). Somar nos totais do ciclo da FR-042 (montados na História 1, antes da lista de
      meses — hoje o detalhe é :96-102): `reapareceram` em "de volta ao Google", `inconclusivos` em
      "sem confirmação", `falhas` em "com falha". Falha ou exceção conta em `errors` (ciclo sai
      `sync_erro`); inconclusivo não. Atualizar a docstring do módulo (linhas 7-8) com o passo novo.
      _Cenários: 9, 13d._ _Fonte: R12; FR-006, FR-040, FR-042; data-model §Rastro._
- [X] T071 [P] [US5] Em `_sync_single_event_flow` (app/calendar/routes.py:4191-4208, já usando
      `consultar_evento` desde a História 1), no desfecho presente: se `event.is_google_missing`,
      chamar `sumico_ops.desmarcar(event, motivo=sumico_ops.MOTIVO_REAPARECEU, actor_name=…,
      actor_role=…)` ANTES de `sync_events([item])` (hoje linha 4206) — nunca dentro de
      `sync_events`. O ator do histórico é quem clicou (data-model §Rastro): a função hoje só recebe
      `event`; acrescentar `actor_name` e `actor_role` keyword-only com default "Sistema", no molde
      de `_delete_event_flow` (:4211-4213), e passá-los no wrapper Jinja `sync_single_event`
      (chamada da linha 4243) a partir de `current_user`. Ausente e inconclusivo continuam sem tocar
      a marca. `sumico_ops` por import tardio; não mover nem renomear nada em routes.py. _Fonte:
      R11, R12; FR-039, FR-006; data-model §Rastro (Reaparecer)._
- [X] T072 [US5] Em `api_sync_event` (app/api/agenda_write.py:621-636), passar o ator a
      `_sync_single_event_flow` na chamada da linha 631: `actor_name=current_user.name` e
      `actor_role=", ".join(r.name for r in current_user.roles)` — o mesmo par já usado nas linhas
      531-532. É o que faz o histórico do evento dizer quem retirou a marca pelo "Sincronizar". O
      endpoint segue sem gate de papel (docstring da linha 624) e devolve o detalhe como hoje
      (:636), agora sem `sumiu_do_google` quando a marca saiu. Não mexer nos ramos `no_google_id`,
      `not_found` e no 409 da História 1. _Fonte: FR-039; data-model §Rastro (Reaparecer); spec
      §RBAC (/sync)._
- [X] T073 [US5] `specs/303-sync-nao-apaga-venda/verify_303.py` — Checkpoint da História 5: com o
      ambiente do quickstart §0 (`DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development`,
      `MANTO_SEM_THREADS=1`, backend local parado), rodar `verify_303.py --ate B2` e `ruff check
      app/calendar app/api`. Esperado: B0, B1 e B2 verdes — o 8 (mesmo registro na data nova, sem
      marca e sem notificação; o sem mudança não é ressincronizado em dois ciclos) e o 9 (marca some
      pela lista e pelo próprio id, aviso lido, histórico diz por quê, aviso novo no segundo sumiço)
      passam a verde, e o 13d (a falha na reconferência não interrompe o ciclo) também. Não seguir
      para a História 2 com vermelho até B2. O verify nunca lê nem escreve no Google de verdade:
      qualquer fuga acusada pelo disjuntor de rede é defeito a corrigir antes de tudo. _Cenários: 8,
      9, 13d._ _Fonte: quickstart §3; plan §Fases (4); Princípio VIII._

**Checkpoint**: adiamento e antecipação não destroem mais o evento; a marca sai sozinha.

---

## Phase 5: História 2 — A equipe não tem como não ver (P1)

**Objetivo**: faixa fixa no topo de toda tela do sistema interno para Superadmin e Comercial (pelo
papel efetivo), com a contagem e o acesso a cada evento marcado.

**Verificação da história (obrigatória)**: `verify_303.py --ate B3` com B0 a B3 em PASS (17);
`npm run typecheck`; a tela é conferida no Polimento.

- [X] T074 [US2] Em app/calendar/sumico_ops.py, criar `FAIXA_LIMITE = 100` e `faixa_sumidos(limite:
      int = FAIXA_LIMITE) -> dict[str, Any]`, devolvendo `{"total", "limit", "items": [{"id",
      "title", "start_at"}]}`. Uma consulta só, por colunas (id, title, start_at, end_at — o fim é
      necessário para o corte), filtrada por `filtro_marcados()`: cancelado nunca conta. `total` é a
      contagem exata; `items` é ordenado em Python por urgência e cortado em `limite`: futuros por
      início crescente; depois passados, do mais recente ao mais antigo; sem data por último.
      "Passado" = fim (ou início, se não houver fim) anterior a `now_sp()` (app/constants.py:291) —
      nunca `utcnow`, que erra 3 h. `start_at` em ISO naive, como `serialize_event_summary`
      (agenda_read.py:82). Sem dinheiro, sem motivo, sem autor. _Cenários: 17._ _Fonte: R8; FR-009,
      FR-033 (parte); contrato GET sumidos-google._
- [X] T075 [P] [US2] Em app/api/agenda.py, criar `_ve_faixa_sumidos() -> bool` — SUPERADMIN ou
      COMERCIAL pelo papel efetivo: `_role_flags(current_user, session.get("impersonate_role"))`,
      chaves `is_superadmin` e `is_comercial` (agenda_read.py:149-177; acrescentar `_role_flags` ao
      import das linhas 14-19) — e a rota `GET /events/sumidos-google` com `@api_login_required`,
      depois de `api_event_detail` (:131-139). Gate no início da view: quem não passa recebe 200
      `{"pode_ver": false, "total": 0, "limit": FAIXA_LIMITE, "items": []}` sem tocar o banco —
      nunca 403; quem passa, `{"pode_ver": true, **faixa_sumidos()}`. `sumico_ops` por import
      tardio, como o arquivo já faz (:55, :126). Atualizar a docstring do módulo (:1-5) com a rota e
      a linha de RBAC. Conferido hoje: o guard do revendedor libera `/api/events/…`
      (app/__init__.py:55 e :747-749) e a rota não colide com `<int:event_id>`. _Cenários: 17._
      _Fonte: R8; FR-009; spec §RBAC; Princípio XIII._
- [X] T076 [P] [US2] Criar frontend/apps/internal/src/lib/sumidosGoogle.ts com: `interface
      SumidoGoogle { id: number; title: string; start_at: string | null }` e `interface FaixaSumidos
      { pode_ver: boolean; total: number; limit: number; items: SumidoGoogle[] }`;
      `useSumidosGoogle()` — `queryKey ["sumidos-google", user.id]` (id de `useCurrentUser`,
      lib/useAuth.ts:28), `apiFetch("/api/events/sumidos-google")`, habilitado só com usuário,
      `refetchInterval` em função do dado (`POLL_MS` de lib/notificacoes.ts:59 enquanto `pode_ver
      !== false`; senão `false`), `refetchIntervalInBackground: false`, `retry: false`;
      `useFaixaSumidosVisivel(): boolean` — observer PASSIVO da MESMA chave (`enabled: false` +
      `select` = `pode_ver && total > 0`); `invalidarSumidosGoogle(queryClient)` pelo prefixo
      `["sumidos-google"]`. Molde: `useNaoLidas` (notificacoes.ts:70-80). Comentar o porquê do
      passivo: cada observer com `refetchInterval` tem timer próprio — dois ativos dariam dois GETs
      por minuto. _Fonte: R9; contrato §Frontend — hooks e §GET sumidos-google (TypeScript)._
- [X] T077 [US2] Criar frontend/apps/internal/src/components/FaixaSumidosGoogle.tsx lendo
      `useSumidosGoogle()`. Dois níveis (R9): wrapper sempre montado `sticky top-14 lg:top-0
      z-[25]`, sem overflow; dentro, `AnimatePresence` com a barra `motion.div` (`overflow-hidden`,
      altura 0↔40 px e opacidade, 200 ms; com `useReducedMotion`, sem transição), cuja linha interna
      é `h-10 bg-red text-on-color`, com ícone `aria-hidden`. Visível só com `pode_ver` e `total >
      0`; sem skeleton, sem erro, sem botão de dispensar. Frase pelo `total` — `1 evento sumiu do
      Google Agenda` / `N eventos sumiram do Google Agenda` — num `span role="alert"` com
      `whitespace-nowrap`. Um evento: a barra é `Link` para `/events/<id>` e, a partir de `sm`,
      mostra ` — <título> · dd/mm/aaaa` (título cortado, data nunca; sem início: `sem data`).
      Comentar o `z-[25]`: acima da régua de abas (`z-20`), abaixo do painel do sino (`z-30`).
      _Fonte: R9; FR-009; plan §Constitution Check XI e §Rastreamento de complexidade; contrato
      §Textos fixos (Faixa)._
- [X] T078 [US2] `frontend/apps/internal/src/components/FaixaSumidosGoogle.tsx` — Em
      FaixaSumidosGoogle.tsx, o caso de vários eventos: a frase vira o botão (`aria-expanded`,
      `aria-controls` com `useId`, indicador de abrir) e a lista é um painel IRMÃO da barra,
      ancorado no wrapper (`absolute top-full`, largura do conteúdo, `max-h-[60vh] overflow-y-auto`,
      animação de até 250 ms) — dentro da barra o `overflow-hidden` o cortaria. Cada linha é `Link`
      para `/events/<id>` com o título em uma linha (reticências; inteiro no `title`) e `dd/mm/aaaa`
      ou `sem data`, na ordem do servidor; se `total > items.length`, última linha sem link `e mais
      N`. Fecha em Esc e em clique fora, devolvendo o foco ao botão (molde:
      NotificacoesBell.tsx:38-58), e ao seguir um item. Armadilha: `formatShortDate(null)` devolve
      "—" (packages/ui/src/lib/date.ts:46-50) — tratar o nulo antes. Em 375 px: uma linha só na
      barra, lista sem rolagem horizontal. _Fonte: R9 (Conteúdo, Tela estreita); FR-009; contrato
      §Textos fixos (Faixa); quickstart §4.2._
- [X] T079 [P] [US2] Em frontend/apps/internal/src/components/AppShell.tsx, montar
      `<FaixaSumidosGoogle />` como irmão ANTES do `<Outlet />` (linha 165), dentro do `AppLayout` —
      os filhos caem no `<main>` sem overflow (packages/ui/src/components/app-layout.tsx:245), então
      o sticky vale pela página inteira e a faixa não remonta na navegação. É o ÚNICO lugar em que o
      hook com poll roda. Montar para todo usuário, inclusive o revendedor: quem decide é o
      `pode_ver` do servidor — não copiar a condição por papel do sino (linha 158). Não tocar no
      `@manto/ui` nem no esqueleto de carregamento (linhas 137-149), que fica sem faixa por
      definição (R9 §Fronteira). _Fonte: R9; FR-009; plan §Código (AppShell.tsx)._
- [X] T080 [P] [US2] Em frontend/apps/internal/src/pages/EventDetailPage.tsx, a régua de abas (linha
      242: `sticky top-14 z-20 … lg:top-0`) passa a somar a altura da faixa quando ela está visível:
      ler `useFaixaSumidosVisivel()` no corpo de `EventDetailPage` (:181) e trocar, com `cn`
      (acrescentar ao import de `@manto/ui`, linha 4 — hoje não é importado), `top-14 lg:top-0` por
      `top-24 lg:top-10`. As duas variantes como strings literais inteiras: o Tailwind não enxerga
      classe montada por interpolação. Manter `z-20` — a faixa é `z-[25]` e fica acima. Atualizar o
      comentário das linhas 237-241 com a conta (56 px da barra do app + 40 px da faixa). O hook
      aqui é o passivo: a página não faz poll. _Fonte: R9; spec §Conferência de tela; docs/04 (todo
      elemento fixo no topo soma a altura da faixa)._
- [X] T081 [P] [US2] Em frontend/apps/internal/src/pages/DashboardPage.tsx, `propsSecao` (linhas
      998-1003) devolve `scroll-mt-28 lg:scroll-mt-14` quando `useFaixaSumidosVisivel()` é
      verdadeiro e o `scroll-mt-16 lg:scroll-mt-4` de hoje (linha 1002) quando não — senão o atalho
      de seção (`irParaSecao`, :983-993, `scrollIntoView` com `block: "start"`) para com o título
      escondido sob a faixa. Chamar o hook no corpo de `DashboardPage` (:932), nunca dentro de
      `propsSecao`. Classes literais inteiras nas duas variantes. Atualizar o comentário das linhas
      995-997: o `scroll-mt` compensa a barra do mobile e, quando houver, a faixa. _Fonte: R9;
      docs/04 (todo elemento fixo no topo soma a altura da faixa)._
- [X] T082 [P] [US2] Em `useRunSync` (frontend/apps/internal/src/lib/adminConfig.ts:131-143),
      acrescentar ao `onSuccess` (linhas 139-141) `invalidarSumidosGoogle(queryClient)`
      (lib/sumidosGoogle.ts) e `invalidarNotificacoes(queryClient)` (lib/notificacoes.ts:54),
      mantendo a invalidação de `admin-sync-status`. Porquê, em comentário: o "Limpar eventos
      fantasma" marca e desmarca em lote, e sem isso o Superadmin que acabou de clicar fica até 60 s
      sem faixa nem sino. _Fonte: contrato §Frontend — hooks (useRunSync); FR-009, FR-010._
- [X] T083 [P] [US2] Em `useSyncEvent` (frontend/apps/internal/src/lib/eventOps.ts:50-58),
      acrescentar ao `onSuccess` (linhas 54-56), depois do `setQueryData(["event", eventId],
      updated)`, `invalidarSumidosGoogle(queryClient)` e `invalidarNotificacoes(queryClient)`: o
      "Sincronizar" pode retirar a marca (FR-039), e a faixa e o sino têm de cair no clique, sem
      esperar o poll de 60 s. Atualizar o comentário da função (:46-49). _Fonte: contrato §Frontend
      — hooks (useSyncEvent); FR-039, FR-010._
- [X] T084 [US2] `specs/303-sync-nao-apaga-venda/verify_303.py` — Checkpoint da História 2: rodar
      `verify_303.py --ate B3` (ambiente do quickstart §0, backend local parado), `cd frontend &&
      npm run typecheck` e `ruff check app/calendar app/api`. Esperado: B0 a B3 verdes; no 17,
      Superadmin e Comercial reais recebem `pode_ver: true` com 1 item (id, título e data, sem
      nenhuma chave de dinheiro); Figurino, Financeiro e revendedor recebem 200 vazio (o Figurino é
      o cenário que DEVE falhar em ver); "Ver como" segue o papel simulado; a ordem é por urgência.
      No 17, "resolvido" é por reaparecimento; "devolvido → faixa vazia" é afirmação do cenário 10
      (História 3). A conferência de tela da faixa (quickstart §4, itens 1, 2 e 10) fica para o
      Polimento. _Cenários: 17._ _Fonte: quickstart §3 e §5; plan §Fases (5); Princípio VIII._

**Checkpoint**: faixa e sino acendem no ciclo em que o sumiço é percebido e apagam quando a marca sai.

---

## Phase 6: História 3 — O Superadmin devolve o evento ao Google (P1), e a FR-045

**Objetivo**: o Superadmin vê o que está em jogo e devolve o evento marcado ao Google, com a escrita
travada fora da produção; enquanto marcado, o evento não pode ser cancelado nem excluído, por nenhum
caminho.

**Verificação da história (obrigatória)**: `verify_303.py --ate B4` com B0 a B4 em PASS (10, 10a a
10i, 11, 12); `npm run typecheck`.

- [X] T085 [US3] Em `app/calendar/sumico_ops.py` (criado na US1), acrescente `class
      DevolverAoGoogleError(Exception)` com dois atributos, `codigo: str` e `message: str` — sem
      status HTTP: quem traduz é a view. Molde: `CancelValidationError`,
      `app/calendar/cancel_ops.py:39-44`. Declare como constantes de módulo o código interno
      `inexistente` (o evento sumiu entre a view e o bloqueio; a view o traduz em 404, sem `codigo`
      no corpo) e os oito códigos do contrato (`cancelado`, `nao_marcado`, `venda_virtual`,
      `sem_data`, `google_travado`, `google_inconclusivo`, `google_desconectado`, `google_recusou`)
      e as nove mensagens da coluna "Mensagem" da tabela de erros de `contracts/api-endpoints.md` —
      `google_recusou` tem duas: a da criação e a da atualização do ramo "já tinha voltado". Copie
      os textos letra por letra; nenhuma mensagem leva erro bruto do Google. _Fonte: R13; contrato
      §devolver-ao-google (tabela de erros); FR-012._
- [X] T086 [US3] `app/calendar/sumico_ops.py` — Em `sumico_ops.py`, escreva `_validar(event:
      CalendarEvent | None) -> CalendarEvent` e `_exigir_ambiente_liberado() -> None`. `_validar`
      levanta `DevolverAoGoogleError` nesta ordem: evento inexistente (código interno
      `inexistente`), `cancelado` (`event.is_cancelled`), `nao_marcado` (`not
      event.is_google_missing`), `venda_virtual` (`_is_virtual_event`, import tardio de
      `app.calendar.routes`, hoje `:2155`), `sem_data` (`start_at` ou `end_at` nulos, ou `end_at <
      start_at`). `_exigir_ambiente_liberado`: `if
      current_app.config.get("CALENDAR_SUPPRESS_EVENT_WRITES", True)` levanta `google_travado` —
      lida de `current_app.config` A CADA chamada (o verify liga e desliga a chave no mesmo
      processo); chave ausente = travado. Nenhuma das duas chama o Google nem escreve no banco.
      _Cenários: 10i, 10f, 10a (ficam verdes com T092)._ _Fonte: R13; R14; FR-012; FR-024._
- [X] T087 [US3] `app/calendar/sumico_ops.py` — Em `sumico_ops.py`, escreva
      `_bloquear_e_revalidar(event_id: int, google_id_consultado: str) -> CalendarEvent`: relê o
      evento com `db.session.query(CalendarEvent).filter(CalendarEvent.id ==
      event_id).with_for_update().populate_existing().one_or_none()` (molde: `bloquear_formulario`,
      `app/formularios/formularios_ops.py:172-186`) e revalida TUDO com `_validar` — outro clique, o
      ciclo ou o "Sincronizar" podem ter desmarcado ou cancelado o evento entre a consulta e o
      bloqueio. Se `google_event_id` já não for o consultado, levante `nao_marcado`. Não comita: o
      bloqueio dura até o commit ou o rollback da devolução. Comente o porquê: sem o bloqueio, dois
      cliques criam dois eventos no Google. `CalendarEvent` não tem relacionamento `lazy="joined"`;
      não acrescente `joinedload` aqui (FOR UPDATE não aceita outer join). _Cenários: 10f (com
      T092)._ _Fonte: R13._
- [X] T088 [US3] `app/calendar/sumico_ops.py` — Em `sumico_ops.py`, escreva
      `_registrar_devolucao_google(event, *, actor, resultado) -> None`, chamada ANTES de qualquer
      escrita no Google. (1) Origem: com os helpers do sync, por import tardio de
      `app.calendar.routes`, veja se há vaga com `role_type != "extra"` cujo
      `strip_role_prefix(character_name)` não está em `parse_characters(event.title)` nem é
      `_is_reserved_title_name` (espelho de `routes.py:2361-2392`); só nesse caso grave
      `event.source = "platform"`. (2) `EventLog` com `actor_name=actor.name`, `actor_role=",
      ".join(papéis)[:60]` e SEM `created_at` (vale o default UTC); os textos fixos do contrato
      (§Textos fixos, "Histórico do evento — devolver": um para `recriado`, outro para
      `reapareceu`), mais a frase do elenco mantido pelo sistema quando a origem mudou. A troca de
      origem vale nos DOIS ramos. (3) `db.session.flush()`. Não comita. _Cenários: 10, 10g (com
      T092)._ _Fonte: R13; FR-044; FR-023; data-model §Rastro._
- [X] T089 [US3] `app/calendar/sumico_ops.py` — Em `sumico_ops.py`, escreva
      `_recriar_no_google(event, *, actor) -> dict`: chama `gcal.insert_event(CALENDAR_ID,
      event.title, event.start_at, event.end_at, description=event.description or "",
      location=event.location or "", all_day=…)` por atributo do módulo (`from app.calendar import
      service as gcal`; `CALENDAR_ID` por import tardio de `routes`). `all_day=True` só quando
      início e fim são meia-noite e `end_at > start_at`. Sem `conference_request_id`, sem
      convidados, sem `extendedProperties`. Exceção, ou resposta sem `id`: `db.session.rollback()`,
      `_log_sync("google_return_failed", event, details=<tipo da exceção>, actor=…, actor_role=…)`,
      `commit` e `google_recusou` com a mensagem fixa da CRIAÇÃO — nunca `str(exc)`. Sem delete
      compensatório; comente o porquê (sem cenário, seria código não verificado). _Cenários: 10,
      10b, 10d, 10h (com T092)._ _Fonte: R13; FR-012; FR-023._
- [X] T090 [US3] `app/calendar/sumico_ops.py` — Em `sumico_ops.py`, escreva
      `devolver_ao_google(event_id: int, *, actor: User) -> dict[str, Any]` (`{"event",
      "resultado"}`; comita) na ordem de R13: `_validar` → `_exigir_ambiente_liberado` →
      `gcal.consultar_evento(CALENDAR_ID, id_velho)` (inconclusivo com motivo `sem_credencial` →
      `google_desconectado`; outro inconclusivo → `google_inconclusivo`) → `_bloquear_e_revalidar` →
      `_registrar_devolucao_google`. Ausente: `_recriar_no_google`; `_log_sync("google_returned",
      …)` ANTES de trocar o id (o detalhe guarda `gcal:<id velho>`; o id novo vai em `details`);
      troque `google_event_id` e `google_html_link` (`created.get("htmlLink")`); `desmarcar(…,
      motivo=MOTIVO_DEVOLVIDO)` (só zera a coluna e marca o aviso como lido); `commit`; resultado
      `recriado`. Entre o insert e o commit, só gravações locais já preparadas (a guarda da 254,
      `routes.py:2190-2208`, cobre 5 minutos). Commit que falha: `rollback`, log do órfão com o id
      novo (molde `agenda_write.py:840-842`) e `google_recusou`. _Cenários: 10, 10e, 10g, 10h (com
      T092)._ _Fonte: R13; FR-012; FR-023; FR-024._
- [X] T091 [US3] `app/calendar/sumico_ops.py` — Em `devolver_ao_google`, implemente o ramo "id velho
      presente" (o evento já tinha voltado): não insira nada. Se `not mesmos_dados(event,
      consulta.item)`, chame `_push_cabecalho_ao_google(event)` (import tardio de
      `app.calendar.event_ops`, hoje `:541-558`) no id velho; falha do push → `rollback`,
      `_log_sync("google_return_failed", …)` com o tipo do erro, `commit` e `google_recusou` com a
      mensagem fixa da ATUALIZAÇÃO (a marca continua). Depois: `_log_sync("google_returned", …)` só
      com o id velho, `desmarcar(…, motivo=MOTIVO_DEVOLVIDO)`, `commit`; resultado `reapareceu`;
      `google_event_id` e `google_html_link` não mudam. Não chame `sync_events` aqui: ele gravaria o
      Google por cima do sistema e reconciliaria o elenco pelo título antigo — o contrário da
      FR-043. Se a orquestradora passar de ~30 linhas, extraia o ramo. _Cenários: 10c (com T092)._
      _Fonte: R13; FR-043; R5._
- [X] T092 [US3] Em `app/api/agenda_write.py`, logo depois de `api_cancelar_evento` (`:541-566`),
      crie `api_devolver_ao_google(event_id)` com
      `@api_bp.route("/events/<int:event_id>/devolver-ao-google", methods=["POST"])` e
      `@api_login_required`: 404 se o evento não existe e, depois, `_can_delete()` → 403 (ordem dos
      vizinhos); corpo vazio. Chame `sumico_ops.devolver_ao_google(event_id, actor=current_user)`
      por import tardio. Sucesso: `result = serialize_event_detail(event, current_user,
      session.get("impersonate_role"))`, `result["devolucao_google"] = {"resultado": …}`,
      `jsonify(result)` — molde em `:845-848`; `_event_detail_json` (`:104-107`) não serve, já
      devolve `Response`. `DevolverAoGoogleError` → `json_error(exc.message, status,
      codigo=exc.codigo)`: 502 para `google_inconclusivo`, `google_desconectado` e `google_recusou`;
      404 (sem `codigo`) para `inexistente`; 409 para os demais. Cite a rota no comentário de RBAC
      do topo (`:6-10`). _Cenários: 10, 10a, 10b, 10c, 10d, 10e, 10f, 10g, 10h, 10i, 11._ _Fonte:
      R13; contrato §devolver-ao-google; spec §RBAC; FR-012; FR-024._
- [X] T093 [P] [US3] Em `frontend/apps/internal/src/lib/agenda.ts`, na interface `EventoDetalhe`
      (hoje `:290`), acrescente a chave de topo opcional `devolucao_google?: { resultado: "recriado"
      | "reapareceu" }`, junto de `flags` (hoje `:349`). Comentário com o porquê: só vem na resposta
      do `POST /api/events/<id>/devolver-ao-google`; é opcional porque backend e bundle sobem
      separados; e só o `onSuccess` da mutação a lê — nenhum componente deve ler essa chave do cache
      depois (o próximo refetch do evento não a traz). _Fonte: contrato §devolver-ao-google
      (TypeScript); R13._
- [X] T094 [P] [US3] Em `frontend/apps/internal/src/lib/eventOps.ts`, depois de
      `useRecusarSolicitacao` (`:169-182`), exporte `type CodigoDevolverAoGoogle` (união literal dos
      oito códigos do contrato) e `useDevolverAoGoogle(eventId)`: `useMutation<EventoDetalhe,
      ApiRequestError, void>` com `POST /api/events/${eventId}/devolver-ao-google`.
      `onSuccess(updated)`: `setQueryData(["event", eventId], updated)` e invalidar `["agenda"]`,
      `["agenda-dia"]`, `["agenda-search"]`, o sino (`invalidarNotificacoes`,
      `lib/notificacoes.ts:54`) e a faixa (`invalidarSumidosGoogle`, `lib/sumidosGoogle.ts`).
      `onError`: se `error instanceof ApiRequestError` e `error.details.codigo` for `nao_marcado` ou
      `cancelado`, invalidar `["event", eventId]` e a faixa. Fechar o diálogo e anunciar ficam com o
      componente. Importe `ApiRequestError` de `@manto/api-client`: os hooks vizinhos tipam `Error`,
      e falha de rede não é `ApiRequestError`. _Fonte: contrato §Frontend — hooks; R15._
- [X] T095 [US3] `frontend/apps/internal/src/components/EventDetail/SumiuDoGoogleBanner.tsx` — Em
      `SumiuDoGoogleBanner.tsx`, para quem tem `flags.can_delete`, acrescente: (1) o quadro "O que
      está em jogo" em `DataRow` (`EventDetail/parts.tsx:98`), do detalhe já carregado, nesta ordem:
      Venda (`kpi.sale_value`), Pago pela cliente (`pagamentos.received_total`; no principal, `Pago
      pela cliente (neste evento)`), Comissão (`kpi.commission`; rótulo `Comissão (estimativa)`
      quando `commission_source` é `estimativa`), BV (`kpi.bv_total`), Escalados (vagas de `elenco`
      com talento); só quando existem: Contrato `anexado`, Comprovantes (quantidade), Grupo
      comercial `principal`/`satélite`; (2) no satélite, as linhas de dinheiro dão lugar à frase
      fixa com link para `/events/<group.leader.id>`; (3) o botão "Devolver ao Google Agenda"
      (`onDevolver`; largura total no celular), inclusive no satélite; (4) a frase fixa do
      Superadmin; (5) `AccordionRow` recolhido com os três passos do contrato. `kpi`, `pagamentos`,
      `elenco` e `group` podem faltar: linha ausente, nunca erro. Dinheiro sempre por `brl()` de
      `EventDetail/parts.tsx` (`@manto/money`, Princípio IX), nunca o número cru. _Fonte: R15;
      FR-011; contrato §Textos fixos._
- [X] T096 [US3] `frontend/apps/internal/src/components/EventDetail/SumiuDoGoogleBanner.tsx` — Em
      `SumiuDoGoogleBanner.tsx`, exporte `DevolverAoGoogleDialog({ title, startAt, endAt, open,
      pending, error, onConfirm, onOpenChange })` sobre o `ConfirmDialog` do `@manto/ui` (não
      destrutivo): título `Devolver ao Google Agenda?` e botão de confirmar `Devolver ao Google
      Agenda`; descrição com `Será recriado como: <título> — <data e horário>`, o aviso de data
      passada e a frase dos convidados e ensaios (textos do contrato); evento sem data mostra `sem
      data` e a recusa do servidor aparece dentro do diálogo. Escreva duas funções puras: o
      formatador de `<data e horário>` nos quatro formatos do contrato (dia inteiro = início e fim à
      meia-noite com fim maior; em vários dias, último dia inclusivo) e "já passou" (o fim — ou o
      início, se não houver fim — é anterior a agora). Não reuse `formatRange` (`parts.tsx:64-68`):
      mostra `00:00 — 00:00` e perde o dia do fim. As datas são horário de parede de São Paulo: leia
      dia e hora da própria string, nunca `toISOString()`. _Fonte: R15; FR-012; contrato §Textos
      fixos (Diálogo)._
- [X] T097 [US3] `frontend/apps/internal/src/components/EventDetail/EventHeader.tsx` — Em
      `EventHeader.tsx`, instancie `useDevolverAoGoogle(event.id)` e o estado `devolverOpen` junto
      dos outros hooks (`:206-214`) — no cabeçalho, não no banner: o banner some no sucesso, e
      callback de `mutate` não dispara em componente desmontado. O `<SumiuDoGoogleBanner>` já está
      montado desde a História 1: passe a ele `onDevolver`; monte `<DevolverAoGoogleDialog>` ao lado
      do `ExcluirEventoDialog` (`:416`). Abrir: `devolver.reset()` e abrir. `onOpenChange` ignora o
      fechamento enquanto `devolver.isPending` (o `ConfirmDialog` só trava o botão Cancelar).
      Confirmar: `devolver.mutate`; no sucesso, fecha e chama `anunciar` (`:217-220`) com o texto do
      contrato conforme `updated.devolucao_google?.resultado`; erro com `codigo` `nao_marcado` ou
      `cancelado` fecha; os demais aparecem dentro do diálogo (`error={devolver.error?.message}`).
      _Fonte: R15; FR-012; SC-004; contrato §Frontend — hooks e §Textos fixos._
- [X] T098 [US3] Em `app/calendar/cancel_ops.py`, logo abaixo de `CancelValidationError` (`:39-44`),
      crie `class EventoMarcadoError(CancelValidationError)` com a mensagem do contrato como padrão
      do construtor: `Este evento sumiu do Google Agenda. O cancelamento com devolução do dinheiro
      chega na próxima entrega — por enquanto, devolva-o ao Google Agenda.` Uma fonte só para o
      texto: a API e o wrapper Jinja leem `exc.message`. Docstring com o porquê: nesta entrega
      nenhum cancelamento de evento marcado sai com a regra velha (decisão do dono, 30/09); a
      segunda entrega troca a recusa pelo "Cancelar e devolver o dinheiro". _Fonte: R16; FR-045;
      contrato §Núcleo._
- [X] T099 [US3] Em `cancelar_evento` (`app/calendar/cancel_ops.py:236`), acrescente como PRIMEIRA
      validação — antes da do motivo (`:262-264`), para a recusa não depender do corpo — `if
      event.is_google_missing: raise EventoMarcadoError()`. Fica antes de qualquer escrita: a
      primeira é `aplicar_estorno_comissao` (`:273`). Vale para qualquer papel, e vem antes da
      recusa do líder de grupo (`:267`). Atualize o `Raises` da docstring (`:259-260`). Não zere a
      marca, não chame `desmarcar` e não mexa em `remover_do_google`: isso é da segunda entrega.
      `solicitar_exclusao` e `recusar_solicitacao` (`:194-233`) NÃO mudam — valem para evento
      marcado e não tocam `google_missing_since`. _Cenários: 12 (cancelar; fecha com T102)._ _Fonte:
      R16; FR-045._
- [X] T100 [US3] Em `_delete_event_flow` (`app/calendar/routes.py:4211-4234`), acrescente como
      primeira linha do corpo — antes do teste de líder (`:4224`) e do `_log_sync("manual_deleted")`
      (`:4226`) — `if event.is_google_missing: raise EventoMarcadoError()`, com import tardio de
      `app.calendar.cancel_ops` (como em `:325`). É o núcleo único dos dois adaptadores (`DELETE
      /api/events/<id>` e o wrapper Jinja), por isso a recusa mora aqui e não na view. Atualize a
      docstring: para evento marcado a função LEVANTA; `(False, None)` continua significando só
      "líder de grupo". Nenhuma outra mudança: `routes.py` não é refatorado. _Cenários: 12 (excluir
      e satélite marcado; fecha com T101 e T103)._ _Fonte: R16; FR-045; contrato §Núcleo._
- [X] T101 [US3] Em `delete_calendar_event` (`app/calendar/routes.py:4318-4341`), envolva a chamada
      a `_delete_event_flow` (`:4327-4331`) em `try/except EventoMarcadoError as exc` (import
      tardio): `flash(exc.message, "error")` e `return redirect(url_for("calendar.event_detail",
      event_id=event_id))` — volta ao evento, como o ramo do líder (`:4332-4337`). Sem o `except`, a
      rota antiga responderia 500. Ela só responde chamando o backend direto (SUPERADMIN; o gate de
      `:4323` não muda) e não passa por `pode_excluir` — é por ela que um marcado com dinheiro seria
      apagado de vez. Jinja vivo: só este toque, sem limpar nada em volta. _Cenários: 12 (rota
      antiga POST /events/<id>/delete)._ _Fonte: R16; FR-045; spec §RBAC; contrato §Endpoints
      alterados._
- [X] T102 [US3] Em `api_cancelar_evento` (`app/api/agenda_write.py:541-566`), importe
      `EventoMarcadoError` junto de `CancelValidationError` (`:554`) e acrescente, ANTES do `except
      CancelValidationError` (`:564`), `except EventoMarcadoError as exc: return
      json_error(exc.message, 409, codigo="sumiu_do_google")`. A ordem importa: a exceção nova é
      subclasse e, capturada depois, viraria 400 com `fields.motivo`. O 404 e o gate `_can_delete()`
      não mudam (papéis inalterados). Atualize a docstring da view com a recusa. _Cenários: 12
      (cancelar pela API)._ _Fonte: R16; FR-045; contrato §Endpoints alterados (cancelar)._
- [X] T103 [US3] Em `api_delete_event` (`app/api/agenda_write.py:504-538`), envolva a chamada a
      `_delete_event_flow` (`:529-533`) em `try/except EventoMarcadoError` →
      `json_error(exc.message, 409, codigo="sumiu_do_google")`. Armadilha: o teste `pode_excluir`
      (`:522-527`) roda ANTES e devolve o 409 genérico, sem `codigo`, para todo marcado com
      dinheiro; para o contrato valer, aplique esse 409 só quando `not event.is_google_missing` — o
      marcado segue para `_delete_event_flow`, que levanta antes de qualquer escrita (exige a recusa
      de `_delete_event_flow` pronta). O satélite marcado sem mais nada passa em `pode_excluir` e é
      recusado pelo núcleo. Atualize a docstring. _Cenários: 12 (excluir pela API; satélite marcado
      sem mais nada)._ _Fonte: R16; FR-045; contrato §Endpoints alterados (DELETE)._
- [X] T104 [US3] `frontend/apps/internal/src/components/EventDetail/EventHeader.tsx` — Em
      `EventHeader.tsx`, enquanto `event.sumiu_do_google` existir: (1) o item "🗑 Excluir ou
      cancelar" do menu (hoje `:308-312`) recebe `disabled: true` e `title` com o texto fixo do
      contrato — `Este evento sumiu do Google Agenda — por enquanto só pode ser devolvido. O
      cancelamento chega na próxima entrega.` (o `KebabMenu` já aceita `disabled` e `title`); (2) o
      botão "Analisar e decidir" do banner de exclusão solicitada (hoje `:390-392`) recebe
      `disabled` e o mesmo `title`. Uma constante para o texto. NÃO mude "🗑 Solicitar exclusão"
      (`:313-322`) nem "Recusar solicitação" (`:393-402`). O servidor continua sendo a trava: um
      bundle antigo mostra a mensagem do 409 dentro do `ExcluirEventoDialog`. _Fonte: R16; FR-045;
      spec §Casos de borda (solicitação em evento marcado); contrato §Textos fixos._
- [X] T105 [US3] `specs/303-sync-nao-apaga-venda/verify_303.py` — Portão da fase, sem editar
      arquivo: no ambiente do quickstart §0 e com o backend local parado, rode
      `.venv\Scripts\python.exe specs\303-sync-nao-apaga-venda\verify_303.py --ate B4` e `cd
      frontend && npm run typecheck`. Esperado: B0 a B4 verdes e nenhuma chamada de rede fora do
      dublê. Cenário do B4 vermelho: corrija o código, não o verify; se o defeito for do verify,
      registre antes de tocar nele. Não use a execução sem argumentos como portão nesta fase: 24 e
      24b ainda são vermelhos (História 6). _Cenários: 10, 10a a 10i, 11, 12._ _Fonte: plan §Fases
      de construção (fase 6 → bloco B4); quickstart §3; Princípio VIII._

**Checkpoint**: o evento marcado tem saída, e só uma. Restam vermelhos 24 e 24b.

---

## Phase 7: História 6 — O elenco sabe que o evento está em confirmação (P2)

**Objetivo**: o artista escalado vê o evento marcado no portal com "Evento em confirmação — entre em
contato com a produção"; evento cancelado sai da avaliação pós-evento.

**Verificação da história (obrigatória)**: `verify_303.py --ate B5` com B0 a B5 em PASS (24, 24b);
portal aberto em 375×812 e em 320 px.

- [X] T106 [P] [US6] Em `app/talent_portal/portal_ops.py`, função `_role_summary` (def em :268;
      dicionário devolvido em :295-328), acrescente a chave `"em_confirmacao"` com
      `bool(event.is_google_missing)` — a propriedade do modelo criada na fase Foundational (marca
      preenchida E não cancelado). Ponha-a logo depois de `"invite_status"` (:317), com comentário
      em pt-BR dizendo o porquê: vai o código, nunca o motivo — o artista não precisa saber de
      "Google" — e a tela escreve o texto. Não mexa nas consultas de `get_agenda` (:353-382) nem de
      `get_historico` (:905-912): o evento marcado não está cancelado e já aparece; as três listas e
      o histórico recebem a chave por esta função (chamadas em :394 e :921). Armadilha: nenhuma
      consulta nova aqui — `event` já vem carregado por `_com_evento()`. _Cenários: 24._ _Fonte:
      R19; FR-022; contrato §Endpoints alterados (GET /api/portal/agenda e /historico)._
- [X] T107 [US6] Em `app/talent_portal/portal_rating_ops.py`, função `_event_ids_in_window`
      (:97-123), acrescente `CalendarEvent.cancelled_at.is_(None)` ao `.filter(...)` de :118 (o
      `join(CalendarEvent)` já está em :117). Efeito: `rateable_event_ids` (:126) e
      `editable_rating_event_ids` (:132) deixam de trazer evento cancelado — e com eles
      `rateable_event_ids` e `editable_event_ids` de `GET /api/portal/ratings/pending`;
      `rated_event_ids` (:92) não muda. Comentário com o porquê: o Histórico já não lista o
      cancelado (`portal_ops.py:909`), então o crachá "Avaliar" acendia para um evento que não
      aparece em lugar nenhum. Assinatura inalterada. Evento marcado (não cancelado) continua
      avaliável — não filtre pela marca. _Cenários: 24b._ _Fonte: R19; FR-022; contrato (GET
      /api/portal/ratings/pending)._
- [X] T108 [US6] Em `app/talent_portal/portal_rating_ops.py`, função `_require_open_event`
      (:225-236), recuse evento cancelado: depois do 404 de quem não está escalado (:232-233) e
      antes da checagem de término (:234-235), levante `PortalRatingError("Este evento foi cancelado
      e não recebe avaliação.", status=400)` quando `role.event.is_cancelled`. Atualize o `Raises`
      da docstring (:228-229). Fecha as três entradas de uma vez — `submit_rating` (:267),
      `submit_rating_detail` (:331) e `serialize_rating_form` (:411);
      `app/api/portal_ratings.py:28-31` já traduz a exceção no envelope de `json_error`, sem
      mudança. Armadilha: a ordem importa — o 404 vem antes, para quem não está escalado não
      descobrir nada do evento; a mensagem é texto fixo do contrato, não a reescreva. _Cenários:
      24b._ _Fonte: R19; FR-022; contrato (GET|POST …/rate, POST …/rate/detail; §Textos fixos)._
- [X] T109 [P] [US6] Em `frontend/apps/portal/src/lib/portalAgenda.ts`, interface `PortalRole`
      (:7-54), acrescente `em_confirmacao?: boolean` depois de `before_event` (:53), com comentário
      JSDoc: verdadeiro quando o evento está em confirmação com a produção; vem o código e a tela
      escreve o texto; opcional pelo mesmo motivo de `role_type` (comentário em :39-45) — backend e
      bundle sobem separados, e sem o campo a tela se comporta como hoje. Não toque
      `lib/portalHistorico.ts`: `PortalHistoricoItem` estende `PortalRole` (:6) e herda o campo.
      Nenhuma mudança nos hooks. _Fonte: contrato §Endpoints alterados; plan.md §Restrições (campo
      novo opcional)._
- [X] T110 [P] [US6] Crie `frontend/apps/portal/src/components/AvisoEmConfirmacao.tsx` (molde de
      documentação: `CacheLine.tsx:5-19` — comentário de topo dizendo por que é componente: fonte
      única do aviso para Agenda, Convites e Histórico). Recebe um booleano opcional e devolve
      `null` quando falso ou ausente. Quando ativo: caixa de largura total com `bg-gold-soft`, texto
      de 14 px (`text-sm`) em `text-gold-ink`, ícone do `lucide-react` com `aria-hidden` e
      `shrink-0`, `role="note"`, e o texto fixo do contrato `Evento em confirmação — entre em
      contato com a produção`, quebrando linha (sem `truncate`, sem largura fixa). Sem botão, sem
      dispensa, sem `style` inline. A palavra "Google" não aparece na tela. Não reaproveite o
      mecanismo "Ciente" — ele zera o aviso. _Fonte: R19; contrato §Textos fixos (Portal); Princípio
      X._
- [X] T111 [P] [US6] Em `frontend/apps/portal/src/pages/PortalAgendaPage.tsx`, componente `RoleCard`
      (:12-103), renderize `<AvisoEmConfirmacao>` com `role.em_confirmacao` como primeira caixa
      depois do cabeçalho do cartão: entre o fechamento do bloco de título, data, local e função
      (:37) e a caixa vermelha "Este evento teve uma alteração" (:39). Importe o componente junto
      dos outros de `../components/` (:5-10). Ele é filho direto do `CardContent` (`space-y-2`,
      :20), fora do `div` `min-w-0` do cabeçalho. Não altere a caixa de alteração nem o botão
      "Ciente" (:39-62). _Fonte: R19 (Posição); FR-022._
- [X] T112 [P] [US6] Em `frontend/apps/portal/src/pages/PortalConvitesPage.tsx`, componente
      `InviteCard` (:18-93), renderize `<AvisoEmConfirmacao>` com `role.em_confirmacao` entre o
      fechamento do cabeçalho (:37, depois de `RoleLine`) e `<CacheLine role={role}
      variant="destaque" />` (:39) — acima do cachê e, portanto, antes de "Aceitar" e "Recusar".
      Importe o componente (:3-5). Os botões de aceitar e recusar (:48-89) não mudam: o convite de
      evento em confirmação continua podendo ser respondido. _Fonte: R19 (Posição); FR-022; spec
      §Casos de borda (convite pendente de evento marcado)._
- [X] T113 [P] [US6] Em `frontend/apps/portal/src/pages/PortalHistoricoPage.tsx`, componente
      `HistoricoRow` (:22-59), renderize `<AvisoEmConfirmacao>` com `item.em_confirmacao` logo
      depois do bloco de título e cachê (fecha em :47) e antes da linha de deslocamento (:49-53) e
      do `<RatingLink>` (:55). Importe o componente (:3-4). Armadilha: o título do histórico usa
      `truncate` (:30) dentro de um `div` `min-w-0` — o aviso fica fora dele, como filho direto do
      `CardContent` (:27), para quebrar linha em 320 px em vez de ser cortado. _Fonte: R19
      (Posição); FR-022._
- [X] T114 [US6] `specs/303-sync-nao-apaga-venda/verify_303.py` — Checkpoint da História 6. Rode `cd
      frontend && npm run typecheck` e, com o backend local parado e as variáveis do quickstart §0,
      `.venv\Scripts\python.exe specs\303-sync-nao-apaga-venda\verify_303.py --ate B5`. Esperado: 24
      verde (o escalado recebe `em_confirmacao: true` em convites, próximos e histórico e ainda
      consegue aceitar; o talento de fora não vê nada; depois de devolvido, sem aviso) e 24b verde
      (cancelado terminado há 2 dias fora de "a avaliar"; a nota volta 400 e não é gravada,
      conferido por conexão separada), sem regressão em B0–B4. Não ajuste o verify para passar: se o
      24b estiver verde sem T107 e T108, o defeito é do verify. _Cenários: 24, 24b._ _Fonte:
      quickstart §3 (bloco B5); spec História 6 §Verificação; Princípio VIII._
- [X] T115 [US6] `frontend/apps/portal/src/components/AvisoEmConfirmacao.tsx` — Conferência do
      portal (skill `manto-conferir-tela`; servidor `manto-portal`, 5174), quickstart §4 item 9, em
      375×812 e em 320 px. Use um talento descartável escalado num evento marcado por `verify_303.py
      --semear-tela` (mês isolado, dublê do Google, vaga que o sistema criou — nunca evento real do
      espelho); ao fim, `--limpar-tela` com o backend parado. Confira o aviso "Evento em confirmação
      — entre em contato com a produção" na Agenda, em Convites e no Histórico (este com evento
      marcado de data passada): primeira caixa depois do cabeçalho; em Convites, antes do cachê e
      dos botões; quebra linha sem rolagem horizontal; "Aceitar" e "Recusar" continuam; a palavra
      "Google" não aparece. Confira `bg-gold-soft` nos dois temas — é o primeiro uso no portal.
      _Fonte: quickstart §4 item 9; spec História 6 §Verificação; R19; Princípio X._

**Checkpoint**: as cinco histórias funcionam; o verify inteiro fecha em `N/N OK`.

---

## Phase 8: Polimento e transversais

- [X] T116 [P] Em `app/calendar/sync.py`, corrija a docstring do módulo (:1-12) e a de
      `run_calendar_sync` (:26-40) para dizerem o que o ciclo faz depois da 303: reconfere os
      eventos marcados pelo próprio id antes do laço de meses; por mês, busca a lista, roda
      `sync_events`, e a limpeza confere no Google cada evento fora da lista — o que mudou de data é
      atualizado, o que tem dinheiro fica e é marcado, e só o vazio com ausência confirmada é
      apagado; o resumo traz os totais do ciclo antes da lista de meses. Tire a frase "a MESMA do
      botão 'Sincronizar agora'" (:7-8): aquele botão não limpa
      (`app/api/admin_config_write.py:64-90`). Só texto; nenhuma linha de código muda nesta tarefa.
      _Fonte: FR-025 (parte); FR-006; FR-042._
- [X] T117 Varredura final dos textos da FR-025, com todo o código pronto. Confira — e corrija o que
      ainda descrever a regra antiga: a docstring de `_cleanup_stale_events` em
      `app/calendar/routes.py` (hoje :342-347, "Remove do banco eventos do mês que foram
      deletados…", e o comentário de :355-358); a docstring de `api_admin_sync_run`
      (`app/api/admin_config_write.py:51`) e a `message` do `cleanup_past` (:112-116 — texto fixo do
      contrato); a confirmação em `frontend/apps/internal/src/pages/AdminSyncPage.tsx:25`. Procure
      prosa remanescente normalizando o texto (juntar linhas quebradas, tirar `#` e `//`, acento e
      caixa) por "fantasma", "sumiu do Google", "não existe mais no Google". Não toque os textos de
      cancelamento e estorno de `cancel_ops.py`: são da segunda entrega. _Fonte: FR-025 (parte);
      contrato §Textos fixos (/admin/sync)._
- [X] T118 `frontend/package.json` — Portão de typecheck: rode `cd frontend && npm run typecheck`
      (um comando, três SPAs — nunca `npx tsc` app a app, que esquece o portal) e corrija até sair
      limpo. Confira por leitura que todo campo novo de payload está opcional no TypeScript
      (`situacao?`, `situacao_desde?`, `sumiu_do_google?`, `devolucao_google?`, os números novos de
      `results[]` do admin, `em_confirmacao?`), que `SituacaoEvento` tem um `export` só
      (`frontend/apps/internal/src/lib/agenda.ts`) e que não entrou nenhum `any`. `tsc` limpo não
      substitui as telas (T115, T122, T123, T124). _Fonte: quickstart §5; constituição §Portões;
      contrato (campos opcionais)._
- [X] T119 Portão de ruff: rode `.venv\Scripts\ruff.exe check app\calendar app\api app\notificacoes
      app\talent_portal app\config.py app\models.py app\constants.py` (quickstart §5) e `ruff
      format` SÓ nos arquivos novos — `app/calendar/sumico_ops.py`,
      `migrations/versions/a7c3e91f4d28_evento_sumiu_do_google.py` e
      `specs/303-sync-nao-apaga-venda/verify_303.py`. Nunca `ruff format` em arquivo que já existia.
      Armadilha: `app/calendar/routes.py` já carrega 8 erros antigos de `ruff check` (docs/05, item
      55, `docs/05_DIVIDA_TECNICA.md:477`), que não são da 303 — o portão é não acrescentar nenhum;
      compare com a saída da `main` e não os limpe de passagem. _Fonte: quickstart §5; plan.md
      Constitution Check II._
- [X] T120 `specs/303-sync-nao-apaga-venda/verify_303.py` — Portão do verify: com o backend local
      parado e as variáveis do quickstart §0 (`DATABASE_URL` de `.local-db-url`,
      `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`, `PYTHONUTF8=1`), rode `verify_303.py` SEM
      argumentos. O portão é a saída `N/N OK`, com o cenário 41 afirmando que nenhuma chamada de
      rede escapou do dublê e que os descartáveis foram apagados. Nenhum cenário pode terminar
      BLOQUEADO nesta altura. Código de saída 2 = sync recente (backend local ligado): pare-o e rode
      de novo; não contorne a guarda. Guarde a saída para a entrada do `docs/03`. _Fonte: quickstart
      §3; spec §Verificação; Princípio VIII._
- [X] T121 `specs/205-loja-interacoes-virtuais/verify_205.py` — Rode de novo
      `.venv\Scripts\python.exe specs\205-loja-interacoes-virtuais\verify_205.py`, agora com o
      código final. Esperado: V7.1 e V7.2 verdes; nenhum `google_event_id` de venda virtual entre os
      ids consultados (é o espião de `consultar_evento` que prova a guarda); a contagem de eventos
      não virtuais do mês igual antes e depois. Não rode os verifies antigos de `scripts/db/` sem
      ajuste: o `verify_151_excluir_sync.py` consultaria o Google real com o token do espelho, e o
      `verify_168_admin_config_react.py` quebra no `cleanup_past`. _Fonte: spec §Portões além do
      verify; quickstart §3; R18._
- [X] T122 `frontend/apps/internal/src/components/FaixaSumidosGoogle.tsx` — Conferência de tela
      (skill `manto-conferir-tela`), quickstart §4 itens 1, 2 e 10, com os eventos semeados por
      `verify_303.py --semear-tela` (nunca marcar evento real do espelho). Faixa como Superadmin e
      como Comercial, em duas telas: fixa no topo ao rolar e depois de navegar a partir de uma
      página rolada; como Figurino: ausente, com um único GET de `/api/events/sumidos-google`. Em
      375×812: logo abaixo da barra do app, sem rolagem horizontal, e o painel do sino cobre a
      faixa. Vários marcados (a semeadura deixa cerca de nove): "N eventos sumiram do Google
      Agenda", no plural; para ver a faixa de um evento só (link com título e data), zerar por SQL a
      marca dos outros semeados (`UPDATE calendar_events SET google_missing_since = NULL WHERE
      google_event_id LIKE 'v303%' AND id <> <um>`) — nunca em evento real; a lista abre sobre o
      conteúdo; cada linha leva ao evento certo; Esc fecha e o foco volta ao botão; em 375, frase
      inteira numa linha, título cortado e data inteira. Movimento reduzido: sem transição. _Fonte:
      quickstart §4 itens 1, 2, 10; spec §Conferência de tela; R9._
- [X] T123 `frontend/apps/internal/src/components/EventDetail/SumiuDoGoogleBanner.tsx` — Conferência
      de tela, quickstart §4 itens 3, 4 e 5, em desktop e em 375×812. Superadmin: banner com a data,
      a frase da edição, o quadro do que está em jogo (comissão dita como estimativa quando for), o
      botão de devolver, a frase do cancelamento e o "recriado à mão" recolhido; régua de abas
      clicável logo abaixo da faixa; "Editar no Google Agenda" ausente; "Sincronizar" responde que o
      evento não está no Google; "Excluir ou cancelar" desabilitado com o motivo; com exclusão
      solicitada: dois banners, "Analisar e decidir" desabilitado, "Recusar solicitação" funciona;
      satélite: frase do grupo com link e botão presente. Diálogo: título e data (dia inteiro como
      "(dia inteiro)"), aviso de data passada, e a mensagem da trava local DENTRO do diálogo.
      Comercial: frase "a decisão é do Superadmin", sem botão; Figurino: só a parte comum. _Fonte:
      quickstart §4 itens 3, 4, 5; R15; R16; FR-024._
- [X] T124 `frontend/apps/internal/src/pages/AdminSyncPage.tsx` — Conferência de tela, quickstart §4
      itens 6, 7 e 8. Agenda: selo "Sumiu do Google" em Lista, Dia e no resultado da busca; só o
      ícone no chip do Mês, com a cor da categoria preservada. Sino: aviso urgente com título, data,
      venda, recebido e escalados; em 375 px o nome do evento e o "recebido" legíveis sem abrir; sai
      da contagem de não lidas quando o evento é resolvido — isto NÃO se confere no local (a
      devolução é travada, e o Sincronizar e a limpeza leem o Google real, onde os ids `v303` não
      existem): está provado no verify (9 e 10, aviso lido), e nunca se liga
      `CALENDAR_ALLOW_LOCAL_EVENT_WRITES` para isso. `/admin/sync`: a confirmação do "Limpar eventos
      fantasma" é o diálogo do sistema (não o do navegador) e o resultado diz os seis números, com
      uma linha por mês que teve algo. Atenção: no ambiente local, confirmar a limpeza LÊ o Google
      real e altera o espelho (FR-024). O item 9 (portal) foi conferido em T115. Confirmar a limpeza
      por último e, ao fim das telas, rodar `verify_303.py --limpar-tela` com o backend parado.
      _Fonte: quickstart §4 itens 6, 7, 8; R7; R10; FR-042._
- [X] T125 [P] Em `docs/00_MAPA_DO_SISTEMA.md` §1, na frase de :24-25 ("As escritas no Google
      acontecem só nos fluxos explícitos de criar/editar/excluir evento"), acrescente a devolução ao
      Google Agenda: o Superadmin recria no Google o evento marcado "Sumiu do Google Agenda"
      (feature 303). A primeira metade continua verdadeira — a sincronização só lê. No cabeçalho
      (:8-10), o head citado está velho (`b7d2e4f1a9c3`): troque pela remissão ao cabeçalho do
      `docs/01`. No roteiro "Mexer no sync do Google" (:280), cite `app/calendar/sumico_ops.py`. Use
      o Edit tool (nunca `Set-Content`, que corrompe os acentos). _Fonte: spec §Docs a atualizar
      (docs/00 §1); FR-012._
- [X] T126 Em `docs/01_SISTEMA_E_BANCO.md`: (1) cabeçalho — abra a linha "Última atualização" (:10)
      com a 303 e a migration `a7c3e91f4d28` como head, empurrando a da 298 para "Antes:" e tirando
      dela o rótulo "head" (:11); o cabeçalho é o lugar do head (§2.11, :600-606 — não toque a
      "Cadeia recente"). Confira com `flask db heads` antes de escrever. (2) §2.2, linha de
      `calendar_events` (:215) — acrescente `google_missing_since` (`DateTime`, nullable; horário de
      parede de São Paulo, como `cancelled_at`; `NULL` = não marcado; "marcado" = preenchida E
      `cancelled_at` nulo; não muda venda, comissão nem escala) e o índice parcial
      `ix_calendar_events_google_missing_since`. _Fonte: spec §Docs a atualizar (docs/01 cabeçalho e
      §2); data-model.md._
- [X] T127 `docs/01_SISTEMA_E_BANCO.md` — Em `docs/01` §3.3 (:686-751): na tabela, acrescente `GET
      /api/events/sumidos-google` (linha dos GET, :689) e `POST /api/events/<id>/devolver-ao-google`
      (linha dos POST, :691); depois do bloco da 299 (:737-751), um bloco "Feature 303": `/sync`
      confere o próprio evento antes de mexer (ausente → 409, nada muda; presente e marcado → retira
      a marca); `PATCH` de evento marcado não escreve no Google; `cancelar` e `DELETE` recusam o
      marcado com 409 `codigo: sumiu_do_google`; resumo da agenda com `situacao` e `situacao_desde`;
      detalhe com `situacao`, `sumiu_do_google` e `google_html_link` nulo em marcado ou cancelado.
      Em §3.11 (:937-940), os números novos de `cleanup_past`. Em §3.13.5 (:1241-1245), o produtor
      `evento.sumiu_google`. Aponte para `contracts/api-endpoints.md`; não copie o contrato inteiro.
      _Fonte: spec §Docs a atualizar (docs/01, contrato dos payloads); contrato; FR-039; FR-045;
      FR-033._
- [X] T128 `docs/01_SISTEMA_E_BANCO.md` — Em `docs/01` §3.15: (1) no parágrafo de
      `portal_ops._role_summary` (:1360-1375), acrescente a terceira chave, `em_confirmacao` —
      booleano, verdadeiro quando o evento está marcado e não cancelado; vai o código, nunca o
      motivo; presente em `pending_invites`, `upcoming` e `history` da agenda e em `items` do
      histórico; opcional no TypeScript, como `role_type` e `before_event` (:1380-1381). (2) em
      "Histórico e avaliações" (:1393-1399): `rateable_event_ids` e `editable_event_ids` de `GET
      /api/portal/ratings/pending` nunca trazem evento cancelado (`rated_event_ids` não muda), e
      `GET|POST …/rate` e `POST …/rate/detail` respondem 400 "Este evento foi cancelado e não recebe
      avaliação." _Fonte: spec §Docs a atualizar (contrato dos payloads: portal); R19; contrato._
- [X] T129 `docs/01_SISTEMA_E_BANCO.md` — Em `docs/01` §4.3, tabela de gates (:1529-1554),
      acrescente: `_ve_faixa_sumidos()` (`agenda.py`, `GET /api/events/sumidos-google`) — SUPERADMIN
      ou COMERCIAL pelo papel efetivo (respeita o "Ver como"); os demais recebem 200 com `pode_ver:
      false`, nunca 403; `_can_delete()` em `POST …/devolver-ao-google` — SUPERADMIN real, depois do
      404; e que `POST /api/events/<id>/sync` segue sem gate de papel e passa a poder retirar a
      marca. Travas de ambiente: em §5.4 (:1866) e na nota de :404, acrescente
      `CALENDAR_SUPPRESS_EVENT_WRITES` (`config._suppress_calendar_event_writes`; escape
      `CALENDAR_ALLOW_LOCAL_EVENT_WRITES`), que cobre SÓ a devolução ao Google. Corrija a linha de
      :1533, que dá `_can_delete()` como COMERCIAL e SUPERADMIN: é só SUPERADMIN (`_CAN_DELETE`,
      `app/calendar/routes.py:64`). _Fonte: spec §RBAC e §Docs a atualizar (docs/01 §4.3, travas de
      ambiente); R8; R13; R14; FR-024._
- [X] T130 Em `docs/02_MAPA_DE_PAGINAS_E_UX.md`: `AppShell` (:191-212) — a faixa fixa "N eventos
      sumiram do Google Agenda" (Superadmin e Comercial pelo papel efetivo, em toda tela dentro do
      shell, sem dispensar; um evento = link, vários = lista; poll de 60 s) e, no item do sino
      (:204-212), o ícone do kind novo e o aviso `urgent` em mais de uma linha; `/agenda` (:312-320)
      — o selo "Sumiu do Google" em Lista, Dia e busca, só o ícone no chip do Mês; `/events/:id`
      (:418-434) — o banner do evento marcado, o botão e o diálogo "Devolver ao Google Agenda",
      "Editar no Google Agenda" ausente e "Excluir ou cancelar" e "Analisar e decidir" desabilitados
      enquanto marcado; `/admin/sync` (:1729) — `ConfirmDialog` e resultado com os seis números.
      Atualize "Última atualização" (:9). _Fonte: spec §Docs a atualizar (docs/02); R9; R10; R15;
      R16; contrato §Textos fixos._
- [X] T131 `docs/02_MAPA_DE_PAGINAS_E_UX.md` — Em `docs/02` §C, tabela de rotas do portal: nas
      linhas de `/portal/agenda` (:1842), `/portal/convites` (:1843) e `/portal/historico` (:1844),
      registre o aviso "Evento em confirmação — entre em contato com a produção"
      (`AvisoEmConfirmacao`, quando `em_confirmacao` é verdadeiro): primeira caixa depois do
      cabeçalho do cartão — na Agenda acima do alerta de alteração, em Convites acima do cachê e dos
      botões (que continuam), no Histórico abaixo de título e cachê e acima de "Avaliar"; sem botão,
      não se dispensa, some quando a marca sai; o texto não cita o motivo. Na linha de
      `/portal/eventos/:id/avaliar` (:1848): evento cancelado não entra no contador "a avaliar" e a
      nota é recusada com a mensagem do contrato. _Fonte: spec §Docs a atualizar (docs/02: portal
      com o aviso); R19; FR-022._
- [X] T132 Em `docs/04_GUIA_DE_DOMINIOS.md` §1: (1) "Fluxo: sincronização" — reescreva o parágrafo
      da limpeza (:88-90): ela confere no Google cada evento fora da lista
      (`service.consultar_evento`, três desfechos), atualiza o que mudou de data, marca o que tem
      dinheiro e só apaga o vazio com ausência confirmada; o núcleo é `app/calendar/sumico_ops.py`,
      `_cleanup_stale_events` virou delegação, e os marcados são reconferidos pelo próprio id antes
      do laço de meses. (2) Crie "Fluxo: Sincronizar de um evento" (hoje só citado em :73-74):
      confere antes de mexer; ausente → nada muda; presente e marcado → tira a marca. (3) "Fluxo:
      exclusão" (:104-109): recusa do evento marcado em `_delete_event_flow` (API e rota Jinja);
      toda exclusão limpa ensaio-filho com histórico e avisos do sino. Na tabela de arquivos do
      domínio (:44-54), acrescente `sumico_ops.py`; e corrija a armadilha de :182-185, que descreve
      um `flash()` em `_delete_event` que já não existe. Cite por nome de função — as linhas citadas
      ali já estão velhas. _Fonte: spec §Docs a atualizar (docs/04: fluxo de exclusão, fluxo do
      Sincronizar); FR-025 (parte); FR-039; FR-045; R4; R12._
- [X] T133 `docs/04_GUIA_DE_DOMINIOS.md` — Em `docs/04` §1 "Invariantes" (lista numerada em
      :113-163; o último é o 12, :142), acrescente os da 303: o sync nunca apaga evento com dinheiro
      (critérios da FR-001); ausência só vale confirmada — inconclusivo não apaga nem marca; mudança
      de data não é sumiço; "marcado" = `google_missing_since` preenchida E não cancelado; evento
      marcado que reaparece sozinho: vale o Google — só a devolução faz valer o sistema (risco
      aceito, com o que acontece ao elenco e às vagas); relógio de cada carimbo
      (`google_missing_since` e `notifications.created_at` em São Paulo; o `EventLog` novo no
      default UTC). Em §8 "Invariantes do frontend" (:508-521): todo elemento fixo no topo soma a
      altura da faixa (40 px). Atualize "Última revisão" (:12). _Fonte: spec §Docs a atualizar
      (docs/04 invariantes); R1; R3; R5; R6; R9; R12._
- [X] T134 Em `docs/05_DIVIDA_TECNICA.md`: risque a dívida 49 (:471 — o sync apagando o principal de
      um grupo e os comprovantes com ele), anotando que a 303 a quitou: pertencer a grupo comercial
      segura o evento (FR-001). Em §9.1 (:347), tire `_cleanup_stale_events` da fatia A: o corpo
      saiu para `app/calendar/sumico_ops.py` e o nome ficou em `routes.py` como delegação de uma
      linha. Não renumere nem reordene os itens existentes (o 61 está fora de ordem em :490, de
      propósito ou não — deixe). _Fonte: spec §Docs a atualizar (docs/05: riscar a 49; §9.1);
      research §Dívida._
- [X] T135 `docs/05_DIVIDA_TECNICA.md` — Em `docs/05`, ao fim da tabela de pendências (depois de
      :490; o maior número hoje é 68 — comece em 69), registre as dívidas de research.md §"O que
      fica registrado como dívida": escritas antigas no Google sem trava; lista do mês sem
      paginação; série recorrente; id velho restaurado da lixeira depois da devolução;
      `update_ensaio` e `edit_ensaio` só capturam `RuntimeError`; ensaio e presente 3D em evento
      cancelado; Fila 3D sem filtro de cancelado; lembrete diário de convite de evento marcado;
      `EventLog` de `cancel_ops` (solicitar, recusar e cancelar) 3 h adiantado; efeito antigo do
      `verify_205` no espelho; sexta cópia do fechar-em-Esc-e-clique-fora; limpeza sem teto de
      consultas; evento sem confirmação ciclo após ciclo sem aviso; ensaio reimportado solto; "já
      trabalhou com a Manto" por evento marcado que não aconteceu; a edição (e o ramo "já tinha
      voltado" da devolução) que transforma dia inteiro em bloco com hora e não apaga local no
      Google; o `docs/01` sem os endpoints da 224; e o estado dos três verifies de `scripts/db/`
      (151, 168, cancelamento). _Fonte: research.md §O que fica registrado como dívida; spec §Fora
      de escopo e §Docs a atualizar (docs/05)._
- [X] T136 [P] Em `docs/PLANO_EXTRACAO_CALENDAR.md`, registre que a limpeza por sumiço já saiu de
      `routes.py`: o núcleo `app/calendar/sumico_ops.py` (feature 303) substitui o que o corte 3,
      "consulta/sync" (:27), previa para a limpeza; a injeção `delete_event_row` em
      `cleanup_stale_events` (:57) deixa de valer como descrita — `sumico_ops` chega a
      `_delete_event`, `sync_events`, `_log_sync` e `_is_virtual_event` por import tardio, exceção
      registrada no plano da 303; e a nota de `sync_single_event_flow` (:58-59) muda: o
      "Sincronizar" passou a usar `consultar_evento`, e o `verify_151_excluir_sync.py` não roda sem
      ajuste. O plano continua pausado; não reescreva os outros cortes. _Fonte: spec §Docs a
      atualizar (PLANO_EXTRACAO_CALENDAR); plan.md Constitution Check I e Rastreamento de
      complexidade (III)._
- [X] T137 [P] Em `DEVELOPMENT.md`, no aviso do `manto_local` (:102-108), acrescente a terceira
      trava: `_suppress_calendar_event_writes` / `CALENDAR_SUPPRESS_EVENT_WRITES` deriva do host do
      banco e cobre SÓ a devolução ao Google (travada, não sai nenhuma chamada — nem a consulta); a
      sincronização, a limpeza e o "Sincronizar" continuam LENDO o Google real no ambiente local, e
      criar, editar, excluir e cancelar evento continuam escrevendo. Diga que o escape
      `CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true` cria evento de verdade na agenda da empresa, que a
      produção importa minutos depois. Acrescente a linha da variável na tabela de variáveis (começa
      em :133): local travado por padrão; nenhuma variável nova no painel de produção. _Fonte: spec
      §Docs a atualizar (DEVELOPMENT.md); R14; FR-024; data-model §Configuração._
- [X] T138 [P] Em `CLAUDE.md` §4, no item das três variáveis, na frase de :97-98 ("As travas
      `_suppress_mail` / `_suppress_calendar_invites` (`app/config.py`) cobrem só e-mail e
      convite"), acrescente a trava nova: `_suppress_calendar_event_writes` cobre só a devolução ao
      Google — todas as outras escritas e todas as leituras do Google seguem sem trava. Uma frase
      só: o arquivo guarda regras e ponteiros; o detalhe fica no `DEVELOPMENT.md` (T137). _Fonte:
      spec §Docs a atualizar (CLAUDE.md §4); FR-024._
- [X] T139 [P] Em `.claude/skills/manto-verify/SKILL.md`, item 3 de "Antes de rodar qualquer coisa"
      (:22-25), acrescente que a trava `CALENDAR_SUPPRESS_EVENT_WRITES`
      (`_suppress_calendar_event_writes`) cobre só a devolução ao Google: a sincronização, a limpeza
      e o "Sincronizar" de um evento continuam lendo o Google real no ambiente local, e criar,
      editar, excluir e cancelar evento continuam escrevendo — um verify que passe por esses
      caminhos não está protegido por ela. Não mude o resto da skill. _Fonte: spec §Docs a atualizar
      (skill manto-verify); FR-024._
- [X] T140 `specs/303-sync-nao-apaga-venda/contagem_pre_deploy.py` — No dia do deploy, antes do
      push: `scripts\db\refresh-local-db.ps1`, depois `contagem_pre_deploy.py --so-sonda` e
      `contagem_pre_deploy.py` (quickstart §1; só leitura — lê o Google real só com `list` e `get`).
      Anote os três números: eventos passados com dinheiro fora do Google; eventos que mudariam de
      data com elenco de convite aceito; inconclusivos. Se algum deixar de ser zero, o deploy sobe
      do mesmo jeito e o "Limpar eventos fantasma" NÃO é rodado até o dono decidir, com a lista. Se
      o Google responder a um apagado com algo que não seja 404, 410 ou `cancelled`, pare: núcleo e
      dublê ganham o caso antes. Depois do refresh a migration local some — rode `flask db upgrade`
      e `python seed.py` de novo. _Fonte: quickstart §1; R17; spec §Casos de borda (evento no
      passado) e §Premissas._
- [X] T141 Em `docs/03_HISTORICO_MUTACOES.md` (append-only; não leia o arquivo inteiro): entrada
      nova no topo do Registro (antes de `### 302`, :287), no formato de :278-280 — motivação, o que
      mudou, RBAC, endpoints, riscos e pegadinhas —, com a migration `a7c3e91f4d28` e os três
      números da contagem do dia do deploy (T140); linha nova no topo da tabela do índice (antes de
      :120); a 303 no "Índice por assunto" (Agenda, :255; Portal do Artista, :262); e o parágrafo
      "Última atualização" (:7). Registre os riscos de research.md §Riscos que o plano carrega,
      entre eles: no intervalo até a segunda entrega é o Superadmin quem retém à mão; quando o
      marcado reaparece sozinho, vale o Google; a resposta perdida no insert (evento órfão criado na
      Agenda); a janela de deploy; o `rollback` do mês só em erro de banco; e sair de SHOW em evento
      marcado apaga os ensaios do Google. _Fonte: spec §Docs a atualizar (docs/03: entrada no topo +
      índice, com a contagem); quickstart §1; CLAUDE.md §6._
- [X] T142 `docs/03_HISTORICO_MUTACOES.md` — Na entrada da 303 do `docs/03` ("Riscos e pegadinhas"),
      registre a nota de revert do quickstart §7: `git revert` do merge é seguro para o schema
      (coluna aditiva e nullable, sem downgrade), mas o código antigo trata o evento marcado como
      comum e o apaga no ciclo seguinte (até 10 minutos), com comprovantes, contrato e escala. Antes
      de reverter: listar os marcados (`google_missing_since IS NOT NULL AND cancelled_at IS NULL`)
      e devolver TODOS ao Google, inclusive os cancelados de verdade. Só reverter com a faixa vazia
      — anotar a lista não preserva nada. _Fonte: quickstart §7; data-model §Migration._
- [ ] T143 `specs/303-sync-nao-apaga-venda/quickstart.md` — Depois do push (só quando o dono pedir;
      à noite, num push só): confirme o backend novo por `GET /api/events/sumidos-google` — 401 sem
      sessão é o novo, 404 ainda é o antigo (nunca pelo `/health`); com sessão de Superadmin,
      `pode_ver: true`. Em seguida, com o dono, o teste do quickstart §6: criar no sistema um evento
      descartável num mês vazio, com venda simbólica; apagá-lo no Google e esperar o ciclo (até 10
      min) — fica marcado, faixa e sino acendem; devolver pela tela — id novo, marca e faixa somem;
      esperar mais um ciclo — um evento só, sem duplicata; tirar a venda e excluir pelo sistema. Se
      a devolução falhar: restaurar o evento na lixeira do Google Agenda e só então excluir. _Fonte:
      quickstart §6; spec §Portões além do verify; research §Riscos; FR-024._

---

## Dependências e ordem

- Setup (T001–T002) → Foundational (T003–T034, bloqueia tudo) → História 1
  (T035–T064) → História 5 (T065–T073) → História 2 (T074–T084) → História 3
  (T085–T105) → História 6 (T106–T115) → Polimento (T116–T143).
- A ordem das histórias é a do plano, não a da prioridade, porque uma depende da outra: a História 5
  precisa da marca (História 1); a devolução (História 3) precisa de `desmarcar` e de `mesmos_dados`
  (História 5) e da invalidação da faixa (História 2); o portal (História 6) fecha o 24 com a
  devolução.
- Dentro da fase: núcleo (`sumico_ops`) antes do endpoint; endpoint antes da tela; checkpoint do
  verify ao fim. A delegação de `_cleanup_stale_events` e os dois consumidores do retorno (`sync.py`
  e `admin_config_write.py`) vão em sequência, sem rodar o ciclo no meio.
- `app/calendar/routes.py` recebe seis toques pontuais, em tarefas diferentes — nunca em paralelo.
- `EventHeader.tsx` é tocado nas Histórias 1 e 3: sempre em sequência.

## Paralelo

- Setup: as duas tarefas.
- Foundational: a migration corre ao lado do `service.py`; as tarefas do `verify_303.py` são um
  arquivo só e vão em sequência; o ajuste do `verify_205.py` é independente.
- História 1: com o núcleo e os endpoints prontos, as tarefas de frontend marcadas [P] (tipos, selo,
  as três visões da agenda, sino, admin) mexem em arquivos distintos.
- História 2: `lib/sumidosGoogle.ts` primeiro; depois, offsets, invalidações e montagem em paralelo.
- História 6: backend e frontend do portal em paralelo.
- Polimento: os documentos marcados [P] são arquivos distintos; os portões e as telas, em sequência.

## Estratégia

- **Entrega única**: as cinco histórias sobem no mesmo deploy. A História 1 sozinha deixaria evento
  marcado sem saída (a devolução é da História 3) e sem faixa (História 2) — ela é o MVP de
  **verificação**, não de deploy.
- **Incremental no verify**: cada fase fecha um bloco (`--ate Bn`), sem regredir os anteriores. Verde
  fora da lista esperada é defeito do verify, não progresso.
- **Portões** (constituição §Portões de Qualidade, obrigatórios mesmo fora desta lista): verify
  `N/N OK` sem argumentos; `verify_205.py`; `npm run typecheck`; `ruff check` sem erro novo; telas
  abertas de verdade; `/speckit-converge`; docs.
- Commit por tarefa ou grupo lógico (`feat(303):`, `docs(303):`), **sempre por caminho** — nunca
  `git add -A`. Merge e push só quando o dono pedir, à noite, num push só.
- Contagem: 143 tarefas — Setup 2, Foundational 32, História 1
  30, História 5 9, História 2 11, História 3 21, História 6
  10, Polimento 28.

---

## Phase 9: Convergence

- [X] T144 Em `specs/303-sync-nao-apaga-venda/verify_303.py`, cenário 9: em (a) e em (d), escalar antes da marca um talento descartável com convite aceito (`_escalar(ev, estado["t"])`), para a conferência "a desmarca sem mudança não manda e-mail" poder falhar — hoje o evento não tem ninguém escalado e a asserção é vazia per spec tabela cenário 9 e Constituição VIII (partial)
- [X] T145 Em `app/calendar/sumico_ops.py::_apagar_vazio`, trocar o início do detalhe da auditoria `auto_deleted` de "Apagado no Google Agenda" para "Não está mais no Google Agenda" — 404/410 pode ser evento movido para outro calendário, e a spec manda nunca afirmar "foi apagado" per spec §Casos de borda e FR-023 (contradicts)
- [X] T146 Em `app/calendar/sumico_ops.py`, docstring do módulo: o GABBY é o evento 1244 (o 1287 é a reimportação sem venda do 1275) per FR-025 (contradicts)
- [X] T147 Em `app/__init__.py::_start_calendar_sync`, tirar da docstring a equivalência com o botão "Sincronizar agora" (que não limpa) e remeter a `app.calendar.sync.run_calendar_sync` — reconfere os marcados, sincroniza e limpa per FR-025 e T116 (partial)
- [X] T148 Em `docs/04_GUIA_DE_DOMINIOS.md`, "Fluxo: sincronização", passo 2: dizer que o evento já marcado é pulado sem consulta e que só o ciclo automático reconfere os marcados pelo próprio id — o "Limpar eventos fantasma" não reconfere per FR-025 e R4 (contradicts)
