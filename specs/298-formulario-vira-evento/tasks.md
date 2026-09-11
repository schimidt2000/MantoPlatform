---
description: "Tasks da feature 298 — O formulário vira evento"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Feature 298 — O formulário vira evento

**Input**: artefatos em `/specs/298-formulario-vira-evento/`

**Pré-requisitos**:
- [plan.md](./plan.md);
- [spec.md](./spec.md), com as histórias e a seção "Verificação" (17 linhas: 1–13, 14a, 14b, 15, 16);
- [research.md](./research.md) (R1–R28) e [data-model.md](./data-model.md);
- os contratos [api-formularios.md](./contracts/api-formularios.md),
  [dashboard-formularios.md](./contracts/dashboard-formularios.md) e
  [pre-evento.md](./contracts/pre-evento.md).

**Revisão**: reescrito em 11/09 depois do `/speckit-analyze`, com os 5 críticos, os 5 altos e os médios
resolvidos e as decisões do dono aplicadas.

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `specs/298-formulario-vira-evento/verify_298.py`
contra `manto_local`, escrito na fase Foundational ANTES dos núcleos. Ele falha pelos motivos certos
e passa ao fim de cada história. Não existe pytest nem `tests/`.

**Organização**: por história da spec (US1–US6). O núcleo de vínculo (R4–R7, R22, R27) é
compartilhado e fica na fase Foundational.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa aberta)
- **[Story]**: história a que a tarefa pertence (US1…US6)

## Regras que valem para TODA tarefa

- **Python.**
  - Type hints e docstring Google; funções de ~30 linhas no máximo; constantes em `app/constants.py`.
  - `except` sempre com log (`# noqa: BLE001 — <motivo>`).
  - `ruff check` nos arquivos tocados; `ruff format` só em `destino_ops.py` e `pre_evento_ops.py`.
- **Núcleo em `app/formularios/*_ops.py`.** Não usa `flask.request`, levanta exceções próprias
  (`FormularioJaTemDestino`, `ValidacaoEncerramento`, `SemTelefone`) e não comita. Quem comita é o
  endpoint ou o comando.
- **Endpoint.**
  - Gate de papel como função no início da view: `_require_vendas` ou `_can_create_event`.
  - Erro sempre no envelope `json_error`.
  - 409 com "Este formulário já tem destino.", salvo reabrir: "Este formulário não está mais
    encerrado.".
  - Todo módulo tocado ganha, ou atualiza, o comentário `RBAC:` no topo.
- **Nomes.** `decisao_humana` é o parâmetro do núcleo que grava `event_link_locked`;
  `bloquear_formulario(id)` é o `SELECT … FOR UPDATE`. "Travar" não se usa para nenhum dos dois.
- **React.**
  - TS estrito, sem `any`; Tailwind e `@manto/ui`, sem `style={{}}` novo.
  - **Todo campo novo do payload é opcional no tipo e lido com fallback** (portão da constituição).
  - Todo botão de ação muda de estado enquanto envia; nunca desabilitar botão por validação.
  - Todo erro de mutation aparece inline em pt-BR, no molde de `FormulariosAdminPage.tsx:494-496`
    (não há toast). No 409, chamar `invalidarDestinoDeFormulario`.
  - Movimento com `useReducedMotion`.
  - `event_date` é data pura: formatar com `formatShortDate`, nunca com `new Date(iso)`. A distância
    em palavras vem de `dias_ate_a_data` / `dias_desde_chegada` do servidor.
  - Mutations recebem o `id` nas variáveis, não no hook.
- **Script contra o `manto_local`.** Roda com `$env:DATABASE_URL = (Get-Content .local-db-url
  -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'`.
- **Google Agenda.** Nenhuma tarefa nem o verify escrevem no Google: o verify troca
  `app.calendar.routes.insert_event` por uma chamada falsa que falha, e todo evento de teste leva
  "[TESTE verify 298] pode apagar" no título. Nunca `DELETE /api/events`.
- **Commits** por caminho (nunca `git add -A`), com mensagem por arquivo (`git commit -F`):
  `feat(298):`, `docs(298):`.

---

## Phase 1: Setup

- [X] T001 Commitar os artefatos de especificação na branch `298-formulario-vira-evento`:
  - arquivos: `specs/298-formulario-vira-evento/{spec,plan,research,data-model,quickstart,tasks}.md`,
    `contracts/*.md`, `checklists/*.md` e `.specify/feature.json`;
  - mensagem: `docs(298): spec, plano, contratos e tarefas`.
- [X] T002 Acrescentar em `app/constants.py`, perto de `VIRTUAL_REFUND_REASON_*` (`:361-368`), as
  constantes de `data-model.md` §3, cada bloco com o porquê:
  - `CORTE_FORMULARIOS_PADRAO = date(2026, 6, 1)`;
  - `FORM_CLOSE_REASON_DESISTIU`, `_REPETIDO`, `_ERRADO`, `_TESTE`, `_OUTRO`, mais
    `FORM_CLOSE_REASONS` (tupla ordenada) e `FORM_CLOSE_REASON_LABELS`, que é a **única** fonte dos
    rótulos (a tela os recebe pela API);
  - `FORM_CLOSE_NOTE_MAX = 300`, `FORM_SUGESTAO_JANELA_DIAS = 3`, `FORM_COR_VERMELHO_ATE_DIAS = 7`,
    `FORM_COR_AMARELO_ATE_DIAS = 30`, `FORM_DATA_SUSPEITA_ANOS = 2`;
  - `FORM_TIPO_ROTULOS = {"comum": "Festa", "corporativo": "Corporativo"}`.

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T003 Em `app/models.py`, classe `FormResponse` (`:1923-1977`):
  - acrescentar `closed_reason` String(30), `closed_note` String(300), `closed_by_id` (FK
    `users.id`, `ondelete="SET NULL"`) e `closed_at` DateTime (UTC, `nullable=True`), com o
    relacionamento `closed_by`;
  - acrescentar `__table_args__` com o índice parcial `ix_form_responses_sem_destino` em
    `created_at`, com `postgresql_where` e `sqlite_where` `event_id IS NULL AND closed_at IS NULL`
    (molde em `models.py:621-630`);
  - atualizar o comentário de `client_link_source` para incluir `'evento'`;
  - criar a classe `FormResponseDismissedEvent`, sem backref (ou com `passive_deletes=True`), com
    `UniqueConstraint("form_response_id", "event_id", name="uq_form_response_dismissed_event")`. A
    docstring explica que as exclusões contam com o CASCADE do banco.
- [X] T004 Escrever à mão a migration `migrations/versions/<rev>_formulario_destino.py`:
  - `down_revision = "c9f4a2b71e60"`, docstring no formato de `c9f4a2b71e60_nfc_moldura_e_recados.py`;
  - `add_column` das 4 colunas via `batch_alter_table`, com FK nomeada;
  - índice parcial;
  - `create_table` dos descartes (as duas FKs em CASCADE, `dismissed_by_id` em SET NULL, UNIQUE);
  - `downgrade` na ordem inversa.

  Aplicar com `.\.venv\Scripts\python.exe -m flask db upgrade` no `manto_local` e conferir que
  `flask db heads` mostra só a revision nova. Nunca `flask db migrate`.
- [X] T005 Escrever `specs/298-formulario-vira-evento/verify_298.py` com as **17 linhas** da tabela da
  spec, a partir do esqueleto de `specs/297-nfc-moldura-e-menu/verify_297.py`.
  - **Ambiente.** `setdefault` de `FLASK_ENV`, `MANTO_SEM_THREADS` e `DATABASE_URL`;
    `limiter.enabled = False`; `_engine_externo` + `_no_banco` para a conexão separada; `_usuario()`
    e `_login()` só por `POST /api/auth/login`; requisições FORA do `app_context`.
  - **Google.** Logo depois do `create_app()`, `import app.calendar.routes as _rotas;
    _rotas.insert_event = _google_falso`. `_google_falso` levanta `RuntimeError("verify 298: Google
    não pode ser chamado")`. A view importa a função na hora da requisição (`agenda_write.py:740`),
    então a troca vale. Todo `CalendarEvent` de teste e todo corpo de `POST /api/events` levam o
    título `"[TESTE verify 298] pode apagar"`.
  - **Usuários descartáveis.** COMERCIAL, FINANCEIRO e CASTING, com o prefixo `__v298_`.
  - **Semeadura direto no banco.**
    - `FormResponse` com `created_at` controlado (inclusive 31/05 23h em SP = 01/06 02:00 UTC);
    - `data` nos DOIS vocabulários: nativo (chaves de `a51ce3dc4f3c`) e WhatsForm (slugs, com
      `data_do_evento` "AAAA-MM-DD HH:MM");
    - `Client` com `normalize_phone`;
    - `CalendarEvent` com `google_event_id` prefixado e `source="platform"`, mais `EventClient`;
    - `Notification` para os usuários descartáveis.
  - **Evento excluído.** `_delete_event(ev, also_from_google=False)` (`app/calendar/routes.py:305`)
    seguido de `db.session.commit()`, porque a função não comita.
  - **Data de início vazia (cenário 1).** Chamar `corte_de_chegada()` com `release_date` nulo num
    `app_context` com `rollback`.
  - **Cenário 14a (sync).** Chamar `retry_auto_link_pending()` num `app_context` curto e conferir só
    os formulários semeados. O efeito nos demais formulários do `manto_local` é aceito: é o mesmo que
    o sync já faz.
  - **Cenário 14b (comandos).** `app.test_cli_runner()`: sem `--execute` confere a contagem; com
    `--execute`, a conexão separada confere o efeito.
  - **Cenário 15 (deve falhar).**
    - CASTING em `/encerrar` recebe **exatamente 403** e FINANCEIRO em `/para-evento` também.
    - `closed_at` continua nulo, conferido pela conexão separada.
    - Controle: COMERCIAL recebe 200 no mesmo formulário.
  - **Limpeza no `finally`.** `apagar_por_entidade("form_response", id)`, respostas, eventos,
    clientes, `form_response_dismissed_events`, `audit_logs` com o prefixo, e `roles.clear()` antes
    de apagar o usuário.
  - **Rodar agora.** Ele deve FALHAR nos cenários não construídos. Salvar a saída em
    `specs/298-formulario-vira-evento/verify_298_primeira_falha.txt`, que vai no commit da
    Foundational.
- [X] T006 Em `app/formularios/formularios_ops.py`, o corte e as partições, sem mudar ainda a forma de
  `count_status` (R1, R2, R28):
  - `corte_de_chegada() -> datetime`: `SiteSetting.release_date` ou `CORTE_FORMULARIOS_PADRAO`,
    meia-noite em `America/Sao_Paulo` convertida para UTC ingênuo;
  - `corte_dia_sp() -> date`: o dia do corte, para servir à tela;
  - `condicao_sem_destino(corte)` e `condicao_particao(nome, corte)`, públicas;
  - `destino_de(response, corte) -> str`, com as mesmas regras das condições (`data-model.md` §4 e §8);
  - `contar_por_destino(corte) -> dict` com `{total, sem_destino, com_evento, encerrados, historico,
    corte}`, numa query só.
- [X] T007 [P] Em `app/notificacoes/notificacoes_ops.py`:
  - `marcar_lidas_por_entidade(entity_type: str, entity_id: int, kind: str | None = None) -> int`:
    UPDATE `read_at = now_sp()` com `read_at IS NULL`, sem filtro de usuário e sem commit (molde
    `:343-355`);
  - `marcar_lidas_por_entidades(entity_type, ids_subquery, kind) -> int`: a mesma coisa em lote, para
    o comando da T049.
- [X] T008 Em `app/formularios/formularios_ops.py`, estender o núcleo `apply_event_link(response, event,
  *, source="manual", decisao_humana=True) -> VinculoResultado` (R4, R5, R26, R27):
  - **Encerramento:** limpa as 4 colunas quando `closed_at` existe.
  - **Cliente**, pelo helper `_cliente_do_evento_para(response, event)`, que escolhe o `EventClient`
    com `Client.phone == response.contact_phone` ou, na falta, `event.client_id`:
    - formulário sem cliente recebe essa cliente, com `client_link_source="evento"`;
    - evento sem cliente (nenhum `EventClient`) recebe a do formulário, via `ensure_event_client`;
    - quando a cliente do formulário não é nenhuma das do evento (**divergem**), não mexe em nada e
      devolve a divergência.
  - **Vínculo:** grava `event_id` e `event_link_source`, `ambiguous=False`, e `event_link_locked=True`
    só com `decisao_humana`.
  - **Sino:** `marcar_lidas_por_entidade("form_response", response.id, KIND_FORM_RESPONSE)`.
  - **Retorno:** `VinculoResultado(divergencia_cliente: dict | None)`, dataclass. Sem commit.
  - **Bloqueio:** helper `bloquear_formulario(response_id) -> FormResponse`, com
    `db.session.query(...).with_for_update()`, e a exceção `FormularioJaTemDestino`.
  - **Callers sem mudança:** `update_event_core` e `set_event_form_response` já chamam o núcleo
    (`event_ops.py:767-771`, `:1011-1014`), e os ajustes de 409 são da T013.
- [X] T009 Em `app/formularios/formularios_ops.py`, os caminhos pelo núcleo:
  - `link_event`: bloqueia; `FormularioJaTemDestino` se `event_id` já existe (não sobrescreve mais);
    chama o núcleo, comita e devolve o resultado.
  - `_attempt_auto_link` (`:651`): `apply_event_link(..., source="auto_date", decisao_humana=False)`.
    A regra de casamento não muda (FR-011).
  - `retry_auto_link_pending` (`:689-714`): acrescenta `FormResponse.closed_at.is_(None)` e usa o
    núcleo com `decisao_humana=False`.
- [X] T010 Em `app/api/formularios_write.py:113-139`, no envio público (R22):
  - `attempt_auto_link_client` roda **antes** de `_attempt_auto_link`, preservando `auto_phone` e o
    `fill_client_from_response`;
  - remover a regravação de `event_link_source` (`:119-120`) e o `ensure_event_client` duplicado
    (`:128-129`), que o núcleo já faz.
- [X] T011 Em `app/calendar/routes.py`, `_link_form_response` (`:3611-3626`) passa a usar
  `bloquear_formulario` + `apply_event_link(response, event, source="manual")`. Se o formulário já tem
  evento, levanta `FormularioJaTemDestino` (defesa; a guarda da T012 barra antes). Sem refatoração
  lateral. Anotar num comentário que a rota Jinja de criação fica sem a guarda, porque `/events` não
  passa pelo `server.js`.
- [X] T012 Em `app/api/agenda_write.py`, `POST /api/events` (`:713-788`): com `form_response_id`,
  `bloquear_formulario` **antes** do `_insert_event` (`:763`), sem nenhum commit até o do
  `_create_event_core`.
  - Formulário já com evento → 409 "Este formulário já tem destino.", sem tocar o Google.
  - `FormularioJaTemDestino` vinda da T011 → 409.
  - Comentar o custo: a linha fica presa durante a chamada ao Google.
- [X] T013 Em `app/calendar/event_ops.py` (`update_event_core` `:767-771`; `set_event_form_response`
  `:1011-1016`): formulário ligado a **outro** evento levanta `FormularioJaTemDestino` (hoje: silêncio
  e `False`), com `bloquear_formulario`. Em `app/api/agenda_write.py`, os dois `PATCH`
  (`/events/<id>` e `/events/<id>/form-response`, `:1036-1058`) mapeiam para 409 com a mensagem
  padrão.
- [X] T014 Em `app/api/formularios_admin_write.py`, `POST .../vincular-evento` (`:50-68`):
  `FormularioJaTemDestino` → 409; resposta `{"response": <resumo>, "divergencia_cliente": ...}`.

  Em `app/api/formularios_admin_read.py`, `_response_summary` (`:38-58`):
  - traz `destino` (por `destino_de`, com o corte calculado uma vez e passado por parâmetro),
    `tipo_rotulo`, `closed_reason`, `closed_reason_label`, `closed_note`, `closed_by_name` e
    `closed_at`;
  - `created_at` e `closed_at` com `+00:00` (R14).

  `list_responses` e `search_responses` passam a `joinedload(client, closed_by)`. **Criar** o
  comentário `RBAC:` no topo dos dois módulos.

**Checkpoint**:
- A migration está no `manto_local`, o núcleo único de vínculo está pronto e o Google fica fora do
  verify.
- Todos os cenários falham pelos motivos certos (endpoint que ainda não existe, bloco da Home no
  formato antigo). Os cenários 10 e 14a exercitam o núcleo, mas dependem do `encerrar` da US2 no
  meio do roteiro: passam ao fim da US2, não aqui (corrigido na implementação, 11/09).
- Commit `feat(298): núcleo único de vínculo, corte e encerramento no banco`, com a primeira falha em
  anexo.

---

## Phase 3: História 1 — A Home mostra só os formulários que precisam de destino (P1) 🎯 MVP

**Objetivo**: o painel substitui os quatro números, com os dois grupos, as cores 0–7/8–30, a distância
em palavras e a ação por papel. A tela Formulários passa a filtrar por destino.

**Verificação da história (obrigatória)**: cenários 1–4 e 13 do `verify_298.py` em PASS; Home aberta
(com e sem pendência, estreita, como FINANCEIRO).

- [X] T015 [US1] Em `app/formularios/formularios_ops.py`, trocar a forma de `STATUS_FILTERS`,
  `_status_condition` e `count_status()` para as partições de T006, com `corte` na contagem. Isso fica
  **no mesmo commit** de T017–T021, com os consumidores. `list_responses` passa a devolver também
  `truncado`. Filtro desconhecido lista todos.
- [X] T016 [US1] Criar `app/formularios/destino_ops.py` com `listar_sem_destino(hoje_sp: date | None =
  None) -> dict` (`data-model.md` §5, `contracts/dashboard-formularios.md`):
  - por formulário: `dias_ate_a_data`, `dias_desde_chegada` (em SP), `grupo`, `data_suspeita`,
    `severidade` e `tipo_rotulo`;
  - ordem: `a_chegar` por data crescente e `ja_passou` decrescente; empate → `created_at`
    decrescente;
  - devolve `{contagens, a_chegar, ja_passou, motivos_encerramento}`.

  Nesta fase cada linha tem um formulário só, e `sugestao` é `None`. Funções pequenas: `_severidade`,
  `_eh_data_suspeita`, `_linha`, `_motivos()`.
- [X] T017 [US1] Em `app/api/dashboard_service.py`, `_painel_formularios` (`:578-585`) chama
  `listar_sem_destino()` dentro do `_bloco` e acrescenta `pode_criar_evento` = `is_superadmin` (`:508`)
  ou `_effective_has_role(user, impersonate, papel)` para algum papel de `_CAN_CREATE`
  (`calendar/routes.py:60`). Gate inalterado.
- [X] T018 [P] [US1] Em `app/api/formularios_admin_read.py`, `GET /api/formularios/respostas`
  (`:69-86`) com os filtros novos, `counts` com as partições e o `corte`, e `truncado`.
- [X] T019 [P] [US1] Tipos do front, com **todos os campos novos opcionais**:
  - `frontend/apps/internal/src/lib/formulariosAdmin.ts`: `StatusFilter`, `StatusCounts` (partições +
    `corte`), `FormResponseSummary` (`destino`, `tipo_rotulo`, `closed_*`, `client_link_source`) e
    `truncado`;
  - `frontend/apps/internal/src/lib/types.ts`: `FormulariosSummary` próprio (`contagens?`,
    `pode_criar_evento?`, `motivos_encerramento?`, `a_chegar?`, `ja_passou?`) e `LinhaFormulario`.
- [X] T020 [US1] Em `frontend/apps/internal/src/pages/DashboardPage.tsx`, o painel "📝 Formulários sem
  evento na agenda" logo depois do "💼 Comercial" (`:859-879`), substituindo o painel atual (`:881-920`)
  e a `LinhaFormularios` (`:409-428`):
  - dois `PanelGroup`, cada um com a sua `ListaTruncada` de 6 linhas;
  - `FormularioSemDestinoRow` local: fundo `bg-red-50`/`bg-gold-50`, `MetricBadge`, e a marca "data
    suspeita" já nesta fase;
  - linha 1: cliente, `formatShortDate(data_informada)` e a distância pelo formatador local a partir
    de `dias_ate_a_data`;
  - linha 2: `tipo_rotulo` · "chegou há N dias";
  - ação principal "Criar evento" ou "Abrir", conforme `pode_criar_evento`;
  - a lista de cada grupo dentro de `AnimatePresence`, com `exit` de 150–350 ms e
    `useReducedMotion`;
  - leitura com fallback (`?.`, `?? 0`, `[]`);
  - `computeSectionStats` (`:532-544`): `count = contagens?.sem_destino ?? 0`, `urgent` = formulários
    das linhas vermelhas, `detail` com o `corte`; o painel lê `statPorSecao.get("formularios")?.urgent`;
  - vazio "Nenhum formulário esperando evento ✓";
  - em tela estreita a linha quebra em duas, sem rolagem horizontal e **com a ação principal sempre
    visível**.
- [X] T021 [US1] Em `frontend/apps/internal/src/pages/FormulariosAdminPage.tsx`:
  - `STATUS_CARDS` (`:171-177`) → "Todas", "Sem destino (desde DD/MM)", "Com evento", "Encerrados" e
    "Histórico (antes de DD/MM)", com o DD/MM do `counts.corte`;
  - grid (`:193`) e `countFor` com as chaves novas;
  - aviso "mostrando os 200 mais recentes — use a busca" quando `truncado`;
  - `SituacaoBadges` (`:225-248`) ganha "Encerrado · <motivo>" e perde "Revisar vínculo";
  - `isFutureWithoutEvent` (`:166-169`) passa a usar o `destino` do servidor.

**Checkpoint**: US1 funcional e verificada sozinha (cenários 1–4 e 13). Commit `feat(298): painel de
formulários sem destino na Home e filtros por destino`.

---

## Phase 4: História 2 — Encerrar um formulário com motivo (P1)

**Objetivo**: encerrar com motivo e reabrir, tudo no histórico de ações; o aviso some ao encerrar.

**Verificação da história (obrigatória)**: cenários 6, 7, 10, 14a e 15 do `verify_298.py` em PASS.

- [X] T022 [US2] Em `app/formularios/destino_ops.py`, funções `encerrar(response_id, motivo, frase,
  usuario)` e `reabrir(response_id, usuario)`, com `bloquear_formulario` e sem commit:
  - **Validação:** motivo ∈ `FORM_CLOSE_REASONS`; frase obrigatória em `outro`, até
    `FORM_CLOSE_NOTE_MAX`. Erro levanta `ValidacaoEncerramento(campo, mensagem)`.
  - **Encerrar:**
    - histórico (`created_at < corte`) → `ValidacaoEncerramento` própria (422);
    - já tem evento ou já está encerrado → `FormularioJaTemDestino`;
    - grava as 4 colunas, marca os avisos como lidos e chama `audit("formulario.encerrado",
      "form_response", id, contact_name, "motivo=...; frase=...")` (`app/utils.py:46`).
  - **Reabrir:** exige que o formulário esteja encerrado (senão, conflito "não está mais
    encerrado"). Limpa as 4 colunas e grava `audit("formulario.reaberto", ...)`. Sem reemitir aviso.
- [X] T023 [US2] Em `app/api/formularios_admin_write.py`, criar `POST .../encerrar` e `.../reabrir`, com
  `_require_vendas`: 400 com `fields`, 404, 409 (mensagem de cada caso), 422 no histórico, 200 com
  `{"response"}` e commit. Registrar no `RBAC:` do topo.
- [X] T024 [US2] Em `app/api/formularios_admin_read.py`, o detalhe (`:100-124`) ganha:
  - `motivos_encerramento`;
  - `flags: {pode_encerrar, pode_reabrir, pode_criar_evento}`: `pode_encerrar` só em `sem_destino`,
    `pode_reabrir` só em `encerrados`, `pode_criar_evento` pelo conjunto `_CAN_CREATE`.
- [X] T025 [US2] Nas libs do front:
  - `frontend/apps/internal/src/lib/notificacoes.ts` exporta `invalidarNotificacoes(qc)` (prefixo
    `["notificacoes"]`);
  - `frontend/apps/internal/src/lib/formulariosAdmin.ts` ganha:
    - `invalidarDestinoDeFormulario(qc, id?)`, que invalida detalhe, lista, busca, `["dashboard"]`,
      `["clientes-metricas"]` e o sino;
    - `useEncerrarFormulario()` e `useReabrirFormulario()`, com o id nas variáveis;
    - a atualização de `useLinkEvent` (`:112-122`) para o retorno `{response, divergencia_cliente}`.

    `invalidateResponse` passa a chamar o helper.
- [X] T026 [US2] Criar `frontend/apps/internal/src/components/formularios/EncerrarFormularioDialog.tsx`
  (usa os hooks da T025):
  - `Dialog` de `@manto/ui`;
  - `<select>` nativo montado a partir de `motivos_encerramento` recebidos por prop (**sem mapa em
    TS**);
  - `<textarea>` que só aparece e é obrigatório em "Outro";
  - erro da API apontado e com foco no campo;
  - botão "Encerrando…" enquanto envia;
  - 409 e 422 viram mensagem inline, e a lista é invalidada.
- [X] T027 [US2] Em `frontend/apps/internal/src/pages/DashboardPage.tsx`, ação secundária "Encerrar…" em
  `FormularioSemDestinoRow`, que abre o diálogo com os motivos do bloco. A linha sai pela animação da
  T020.
- [X] T028 [US2] Em `frontend/apps/internal/src/pages/FormulariosAdminPage.tsx`, seção "Destino" no
  `ResponseDetailDialog` (`:501-612`):
  - encerrado: motivo, frase, quem e quando, e o botão "Reabrir";
  - sem destino: botão "Encerrar";
  - obedece às `flags`; erros inline.

**Checkpoint**: US1 e US2 independentes. Commit `feat(298): encerrar e reabrir formulário com motivo`.

---

## Phase 5: História 3 — Formulários da mesma cliente numa linha só (P2)

**Objetivo**: agrupar pelo telefone e deixar a comercial escolher qual vale.

**Verificação da história (obrigatória)**: cenário 5 do `verify_298.py` em PASS.

- [X] T029 [US3] Em `app/formularios/destino_ops.py`, `listar_sem_destino` passa a agrupar por
  `contact_phone`:
  - sem telefone → `chave="id:<id>"` sozinho;
  - representante = `created_at` mais recente; `repetido`; `formularios[]` com tipos misturados;
  - `outro_com_evento`, numa consulta em lote por `contact_phone IN (...)`.
- [X] T030 [US3] Em `app/formularios/destino_ops.py`, `manter_entre_repetidos(response_id, usuario) ->
  list[int]`:
  - bloqueia o mantido e os demais sem destino do mesmo telefone desde o corte;
  - 409 se o mantido já tem destino; `SemTelefone` → 422;
  - encerra os demais como `repetido`, com `audit()` por formulário e o sino marcado como lido.

  Em `app/api/formularios_admin_write.py`, criar `POST .../manter-entre-repetidos`, com
  `_require_vendas`.
- [X] T031 [US3] No front:
  - hook `useManterEntreRepetidos()` em `frontend/apps/internal/src/lib/formulariosAdmin.ts`;
  - em `frontend/apps/internal/src/pages/DashboardPage.tsx`, as marcas na ordem fixa; a expansão
    (`motion.div` com `useReducedMotion`, molde `ListaTruncada` `:193-224`) lista os formulários com
    "Este é o que vale"; erros inline.

**Checkpoint**: US3 verificada (cenário 5). Commit `feat(298): formulários da mesma cliente numa linha
só`.

---

## Phase 6: História 4 — "Parece ser este evento, é?" (P2)

**Objetivo**: sugerir o evento da cliente a até 3 dias; confirmar, ou descartar para sempre com
confirmação.

**Verificação da história (obrigatória)**: cenário 8 do `verify_298.py` em PASS.

- [X] T032 [US4] Em `app/formularios/destino_ops.py`, `sugerir_eventos(linhas) -> None` (R10):
  - **uma** consulta de candidatos para todos os telefones:
    - `cancelled_at IS NULL`, fora de ensaio e **não satélite** (`group_leader_id IS NULL`);
    - `NOT EXISTS` formulário ligado;
    - `EventClient` → `Client.phone IN (...)`;
    - sem par descartado;
  - em Python: |dias| ≤ `FORM_SUGESTAO_JANELA_DIAS`, menor diferença, empate → o mais cedo;
  - chamar dentro de `listar_sem_destino`, mais a irmã `sugestao_para(response)` para o detalhe.
- [X] T033 [US4] Em `app/formularios/destino_ops.py`:
  - `confirmar_sugestao(response_id, event_id)`: bloqueia; valida que o evento continua candidato
    (404/409); chama `apply_event_link(..., source="manual")` e devolve `VinculoResultado`;
  - `descartar_sugestao(response_id, event_id, usuario)`: `INSERT … ON CONFLICT DO NOTHING` (ou
    captura `IntegrityError` com `rollback` e log) e devolve sempre OK.

  Em `app/api/formularios_admin_write.py`, criar `POST .../sugestao/<event_id>/confirmar` e
  `.../descartar`. O detalhe ganha `sugestao`.
- [X] T034 [US4] No front:
  - hooks `useConfirmarSugestao()` e `useDescartarSugestao()`;
  - em `frontend/apps/internal/src/pages/DashboardPage.tsx`, a faixa "Parece ser o evento de DD/MM —
    [Ligar] [Não é este]", com entrada e saída em `motion` e `useReducedMotion`:
    - "Não é este" abre um `ConfirmDialog` ("A sugestão não voltará para este formulário; ainda dá
      para ligar à mão pela tela Formulários") com estado de envio;
    - depois de "Ligar", se vier `divergencia_cliente`, a faixa mostra as duas clientes e "Usar a
      cliente do evento neste formulário" (hook da T046);
  - `frontend/apps/internal/src/pages/FormulariosAdminPage.tsx` mostra a mesma sugestão no detalhe.

**Checkpoint**: US4 verificada (cenário 8). Commit `feat(298): sugestão de evento da cliente a até 3
dias`.

---

## Phase 7: História 5 — Criar o evento a partir do formulário, conferindo (P2)

**Objetivo**: o cadastro abre preenchido, nos dois formatos, com as marcas e os alertas, sem salvar
nada sozinho e sem botão desabilitado.

**Verificação da história (obrigatória)**: cenários 11 e 12 do `verify_298.py` em PASS; cadastro
aberto a partir de um formulário do site, um da carga WhatsForm e um corporativo, **sem salvar**.

- [X] T035 [US5] Criar `app/formularios/pre_evento_ops.py` com `extrair_para_evento(response) -> dict`
  (`contracts/pre-evento.md`):
  - **Leitura das chaves:** constante `SINONIMOS` (chaves nativas e slugs WhatsForm), lida com
    `_valor(response, *chaves)`.
  - **Data e hora:** `date` vem da coluna; `start` vem de `hora_evento` ou da hora dentro de
    `data_do_evento`.
  - **Fim (`_parse_periodo`):** só formas inequívocas; o resto vira alerta com o texto.
  - **Local:** no corporativo, o endereço do evento, nunca o da empresa.
  - **Tipo:** `R&I`, `SHOW` ou `CORP`; não reconhecido → alerta `tipo_sem_correspondente`.
  - **Pagamento:** tabela constante sobre `" ".join(strip_accents_lower(s).split())`.
  - **Cliente:** ficha do formulário; senão sugerida pelo telefone; senão `quick_create_client`.
  - **Observações e elenco:** `observacoes` rotuladas; `characters` divididos.
  - **Alertas:** `data_suspeita`, `hora_ausente`, `periodo_ambiguo`, `endereco_incompleto`,
    `sem_correspondente` e `tipo_sem_correspondente`.
  - **`eventos_da_cliente`:** desde o corte, não cancelados, fora de ensaio, **não satélite**, sem
    formulário, com cliente do mesmo telefone.
  - **Nunca** valor, vendedor nem título.
- [X] T036 [US5] Em `app/api/formularios_admin_read.py`, `GET .../para-evento`:
  - gate pelo conjunto `_CAN_CREATE` (import tardio de `app.calendar.routes`, sem duplicar a regra);
  - 403, 404, e 409 se já tem evento;
  - só leitura, sem `marcar_lidas_por_objeto`.
- [X] T037 [P] [US5] Em `frontend/apps/internal/src/lib/formulariosAdmin.ts`, tipos `ParaEvento`,
  `AlertaFormulario` e `ObservacaoRotulada` (campos opcionais), e o hook `useParaEvento(id)` (query
  `["formularios-para-evento", id]`).
- [X] T038 [US5] Props opcionais nos blocos do cadastro (usa os tipos da T037), sem mudar quem não as
  passa:
  - `frontend/apps/internal/src/components/EventFormBlocks/{DadosEventoBlock,PagamentoBlock,ClienteBlock,ObservacoesBlock}.tsx`
    aceitam `doFormulario?: ReadonlySet<string>` e `alertas?: AlertaFormulario[]`: a marca "do
    formulário" e o alerta com o texto da cliente, no campo;
  - `ClienteBlock` repassa `cadastroRapidoInicial?` ao `frontend/apps/internal/src/components/ClientPicker.tsx`,
    que abre o cadastro rápido sozinho (`creating`), e o `QuickCreateClientForm` ganha email e
    CPF/CNPJ, que o `QuickCreateClientInput` já aceita (`lib/clientes.ts:100-110`).
- [X] T039 [US5] Em `frontend/apps/internal/src/pages/EventCreatePage.tsx`, com `?form_response_id=`,
  trocar `useFormResponseDetail` (`:61-67`) por `useParaEvento`:
  - **Preenchimento:**
    - efeito chaveado por `[paraEvento.data?.form_response?.id]`, com `setValue` campo a campo (ou
      `reset({...getValues(), ...valores})`), **nunca** zerando `sale_date` (hotfix 267b) nem
      `seller_id`;
    - skeleton enquanto carrega;
    - preenche `characters`, `clients` / cadastro rápido e `observations` rotuladas (nunca
      `description`);
    - aviso "Preenchido a partir do formulário de <nome> — confira os campos marcados".
  - **Data suspeita:**
    - o Salvar **sempre ativo**;
    - explicação ao lado da data desde o início;
    - no envio sem confirmar nem trocar, `setError("date", …)` com a explicação, e o efeito de foco
      existente (`:265-275`) leva até ela;
    - a caixa "A data está certa" limpa a exigência.
  - **`eventos_da_cliente`:** faixa com "Ligar a este evento", que chama o `useLinkEvent`. Se vier
    `divergencia_cliente`, mostrar as duas clientes antes de navegar.
  - **Erros:** 409 vira mensagem inline, e o botão não reenvia.
  - Corrigir o comentário de RBAC (`:58-60`).
- [X] T040 [US5] Em `frontend/apps/internal/src/lib/eventCreate.ts` (`useCreateEvent`/`useUpdateEvent`
  `:187-212`) e `frontend/apps/internal/src/lib/eventInline.ts` (`useSetEventFormResponse`
  `:104-110`), invalidar `["dashboard"]`, `["formularios-respostas"]` e o sino, com
  `invalidarDestinoDeFormulario` (T025).

**Checkpoint**: US5 verificada (cenários 11 e 12). Commit `feat(298): criar evento a partir do
formulário, conferindo`.

---

## Phase 8: História 6 — A cliente vem junto, e o aviso do sino some sozinho (P3)

**Objetivo**: divergência resolvida pela comercial, nenhum aviso para formulário que nasce ligado, e as
correções únicas.

**Verificação da história (obrigatória)**: cenários 9 e 14b do `verify_298.py` em PASS.

- [X] T041 [US6] Em `app/formularios/destino_ops.py`:
  - `usar_cliente_do_evento(response_id)`: exige evento com cliente (409); usa a escolha do núcleo;
    não toca o evento;
  - `divergencia_de(response) -> dict | None`: formulário e evento com cliente, e a do formulário fora
    dos `EventClient`.

  Em `app/api/formularios_admin_write.py`, criar `POST .../usar-cliente-do-evento`. O detalhe ganha
  `divergencia_cliente`.
- [X] T042 [US6] Em `app/notificacoes/notificacoes_ops.py`, `notificar_resposta_formulario` (`:195-212`)
  devolve 0 sem emitir quando `response.event_id` já existe (FR-016), com o porquê comentado.
- [X] T043 [US6] Em `frontend/apps/internal/src/lib/formulariosAdmin.ts`, hook
  `useUsarClienteDoEvento()`. Em `frontend/apps/internal/src/pages/FormulariosAdminPage.tsx`, o aviso da
  divergência no detalhe e depois do vínculo pela `EventoSection` (lido do `data` do `useLinkEvent`),
  com o botão "Usar a cliente do evento neste formulário".
- [X] T044 [US6] Em `app/cli.py`, criar `flask formularios-avisos-resolvidos [--execute]` (FR-019):
  - conta os `Notification` com `kind=notificacoes_ops.KIND_FORM_RESPONSE`, não lidos, de formulário
    com evento ou encerrado;
  - com `--execute`, `marcar_lidas_por_entidades` em lote e commit;
  - saída em pt-BR; molde de dry-run em `app/cli.py:835-852`.
- [X] T045 [US6] Em `app/cli.py`, criar `flask formularios-cliente-do-evento [--execute]` (FR-020):
  - seleção: formulários desde o corte, com evento, `client_id IS NULL`, e evento com cliente;
  - conta sem `--execute`;
  - com `--execute`, aplica `_cliente_do_evento_para` (T008) com `client_link_source='evento'` e
    comita.

**Checkpoint**: todas as histórias verificadas. Commit `feat(298): cliente divergente, sino que nasce
apagado e correções únicas`.

---

## Phase 9: Polimento e transversais

- [X] T046 `cd frontend && npm run typecheck` limpo (três SPAs) e `.\.venv\Scripts\ruff.exe check` nos
  Python tocados. `ruff format` só em `destino_ops.py` e `pre_evento_ops.py`.
- [X] T047 `verify_298.py` **17/17**, com o cenário 15 recusado (403 exato), o controle 200 e a escrita
  por conexão separada. Saída anotada no commit.
- [X] T048 Conferência de tela no Browser pane (skill `manto-conferir-tela`), com print para o dono:
  - Home: com e sem pendência, estreita, repetida, sugestão, "Não é este", saída animada, movimento
    reduzido, e como FINANCEIRO;
  - tela Formulários: cartões, encerrar "Outro" sem frase, reabrir, divergência;
  - cadastro a partir de um formulário do site, um da carga WhatsForm e um corporativo (data 2049,
    "Boleto", Salvar sem confirmar marca o campo), **sem salvar**.
- [X] T049 [P] `docs/01_SISTEMA_E_BANCO.md`:
  - head da migration no cabeçalho;
  - §2.7 `form_responses` e a tabela de descartes;
  - endpoints novos e alterados (`:1188-1203`), inclusive os dois `PATCH` de evento e o envio
    público;
  - §3.2, o bloco `formularios`;
  - §4.3 RBAC, uma linha por endpoint;
  - notificações e os dois comandos.
- [X] T050 [P] `docs/02_MAPA_DE_PAGINAS_E_UX.md`: Home (`:226-271`), `/formularios` (`:1331-1374`) e
  `/events/new` (`:283-332`).
- [X] T051 [P] `docs/04_GUIA_DE_DOMINIOS.md`, na linha de Formulários (`:412`): a invariante do
  destino, o corte pela chegada, o núcleo único de vínculo, e a correção da citação de
  `_attempt_auto_link`.
- [X] T052 [P] `docs/05_DIVIDA_TECNICA.md`:
  - registrar a limpeza de dados pendente (datas 2029–2049, comprovantes sem valor, evento 309);
  - o agrupamento que falha com celular antigo sem o 9º dígito;
  - a rota Jinja de criação de evento sem a guarda de 409;
  - atualizar 4.2.
- [X] T053 `docs/03_HISTORICO_MUTACOES.md`: entrada no topo "298 — O formulário vira evento"
  (motivação; decisões de 10/09 e 11/09; pegadinhas: `created_at` em UTC, três caminhos fora do
  núcleo, Google antes do banco, dois vocabulários de chave, `formatRelativeDay` com o relógio do
  navegador), mais a linha no índice.
- [X] T054 Executar a parte local do `quickstart.md` (§1–§3), inclusive os dois comandos no
  `manto_local` (sem e com `--execute`, conferindo por consulta).
- [ ] T055 Commit `docs(298): documentação viva`, por caminho. Depois `/speckit-converge`. Quando o dono
  pedir o push, seguir a skill `manto-deploy`:
  - portão "antes de em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`,
    `migrations/versions/` sem untracked, sonda `/api/`;
  - os dois comandos no `manto-backend`, primeiro contando e depois com `--execute`.

---

## Dependências e ordem

- **Ordem geral:** Setup (T001–T002) → Foundational (T003–T014) → US1 → US2 → US3 → US4 → US5 → US6 →
  Polimento.
- **Foundational:**
  - T003 e T004 vêm antes do verify (T005);
  - T006–T014 dependem de T003 e T004;
  - T007 é paralela a T006;
  - T010–T013 dependem de T008 e T009.
- **Entre histórias:**
  - US1 é o MVP.
  - US2 depende de T008 e usa a linha e a animação da US1 (T020).
  - US3 e US4 estendem `listar_sem_destino` (T016) e a linha.
  - US4 (T034) usa o hook de divergência da US6 (T043); se a US6 ainda não existir, a faixa mostra
    só as duas clientes, sem o botão.
  - US5 depende de T011–T012 e **usa `invalidarDestinoDeFormulario` (T025, US2)**, então vem depois
    da US2.
  - US6 depende do núcleo e das telas da US1 e da US2.
- **Dentro de cada história:** `_ops` → endpoint → tipos/hooks → tela → verify em PASS.

## Paralelismo possível

- **Foundational:** T007 com T006.
- **US1:** T018 e T019, depois de T015–T017.
- **US5:** T037 com T035/T036. T038 espera T037, e T039 junta tudo.
- **Polimento:** T049–T052 (documentação).

## Estratégia

- **MVP:** Setup + Foundational + US1. A Home deixa de mostrar 1.347 e passa a mostrar ~36 formulários
  com nome e data.
- **Incremental:** US2 (encerrar) → US3 e US4 (a lista encolhe sozinha) → US5 (acaba a redigitação) →
  US6 (cliente, sino e correções únicas).
- **Verify:** cada história fecha com os seus cenários em PASS antes da próxima.
- **Publicação:** só quando o dono pedir (merge + push = deploy). O deploy fica para depois, por
  decisão do dono. Os campos opcionais no React protegem a janela em que servidor e site ficam em
  versões diferentes.
