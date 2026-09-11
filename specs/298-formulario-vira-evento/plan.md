<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Feature 298 — O formulário vira evento

**Branch**: `298-formulario-vira-evento` | **Data**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/298-formulario-vira-evento/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3.0.0) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

Todo formulário que chegou desde a data de início do sistema (01/06/2026) passa a ter um de três
destinos: ligado a um evento, encerrado com motivo, ou visível como tarefa na Home. A lista vive num
painel próprio, com dois grupos, cores por proximidade, formulários da mesma cliente numa linha e
sugestão de evento a até 3 dias.

**Abordagem** (detalhe em [research.md](./research.md)):
1. **Estado sem coluna de status.** O estado vem de quatro colunas novas de encerramento e de um
   corte por `created_at`, que está em UTC. Quatro partições que se excluem alimentam, pela mesma
   função (`count_status`), a Home e a tela Formulários.
2. **Um núcleo único de vínculo** (`apply_event_link`), pelo qual passam a entrar os três caminhos
   que hoje escrevem direto: criar evento, envio público e sync. Na mesma transação ele leva a
   cliente nos dois sentidos, limpa o encerramento e marca como lido **para todos** o aviso do sino.
3. **A Home recebe as linhas prontas do servidor.** A severidade é calculada em horário de São
   Paulo, e as sugestões saem em lote.
4. **"Criar evento" chama um extrator puro** que entende os dois vocabulários de chave (nativo e
   carga WhatsForm). O cadastro abre preenchido, com cada campo marcado e os alertas.

**Mudança de contrato deliberada.** Ligar um formulário que já tem evento passa a responder 409, e
não mais a sobrescrever. O `POST /api/events` também responde 409 antes de tocar no Google.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack
Query, Tailwind CSS, shadcn/ui (`@manto/ui`), Framer Motion, `@manto/api-client`
(`apiFetch`/`assetUrl`), `@manto/money`. Nenhuma dependência nova.

**Armazenamento**: PostgreSQL — produção no Render (`manto-postgres`, `render.yaml`); verificação
contra a cópia `manto_local`. Migration aditiva sobre o head `c9f4a2b71e60`.

**Verificação**: `specs/298-formulario-vira-evento/verify_298.py` contra `manto_local` (login só pela
API; escrita por conexão separada; 17 linhas — 1–13, 14a, 14b, 15 e 16 —, com o 15 devendo falhar). Também
`cd frontend && npm run typecheck` e tela aberta no Browser pane (Home, Formulários, criar evento).

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs servidas por `frontend/server.js`);
staff em desktop, público e portal em smartphone

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**:
- A Home ganha 5 consultas fixas, nenhuma por linha:
  - o corte (`SiteSetting`), lido uma vez por requisição;
  - as contagens (`count_status`);
  - os formulários sem destino, com `joinedload(client)`;
  - os candidatos a sugestão, em lote;
  - os formulários "com evento" da mesma chave.

  Hoje são ~36 linhas.
- A lista da tela Formulários faz `joinedload(client, closed_by)`, e o corte vem calculado uma vez e
  passado ao serializador.
- O índice parcial cobre o `sem_destino`.

**Restrições**:
- `created_at` em UTC contra um corte em horário de São Paulo.
- O `POST /api/events` escreve no Google, então o verify não o chama com efeito.
- A regra de vínculo automático não muda (FR-011).
- Datas puras com `formatShortDate`, nunca `new Date(iso)`.
- `useReducedMotion` nas expansões.
- Nenhuma rota pública nova, então `frontend/server.js` não muda.

**Escala/escopo**:
- **Banco:** 1 tabela nova (`form_response_dismissed_events`), 4 colunas em `form_responses` e 1
  índice parcial.
- **Endpoints:** 7 novos (encerrar, reabrir, manter entre repetidos, confirmar sugestão, descartar
  sugestão, usar a cliente do evento, dados para evento) e 9 alterados:
  - `GET /api/dashboard`;
  - lista, busca e detalhe da tela Formulários;
  - `vincular-evento`;
  - `POST /api/events`;
  - envio público `POST /api/formularios/<tipo>`;
  - `PATCH /api/events/<id>` e `PATCH /api/events/<id>/form-response`.
- **Comandos:** 2 CLI de correção única (`formularios-avisos-resolvidos` e
  `formularios-cliente-do-evento`), ambos só contam sem `--execute`.
- **Telas:** 3 (Home, Formulários, criar evento).

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Reusa `apply_event_link`/`ensure_event_client` (`formularios_ops.py:185-283`) como porta única; `count_status`/`_status_condition` (:130-163) como fonte única das contagens; `_event_client_phones` (:618) e `normalize_phone` (`clientes/importer.py:43`); `compute_comercial_pending` (`dashboard_service.py:270-345`) como molde da lista; `SectorPanel`, `PanelGroup`, `ListaTruncada`, `MetricBadge`, `Dialog`, `formatShortDate`/`formatRelativeDay`; o esqueleto da `verify_297.py`; a guarda 409 do orçamento (`agenda_write.py:746-760`); `with_for_update` (`virtuais_ops.py:763`); `audit()` (`app/utils.py:46`, sem commit) para o histórico de encerrar e reabrir. Novo só o que não existe: encerramento, sugestão, extrator, "lida para todos". A lista de motivos de encerramento é servida pelo servidor, uma fonte só, sem cópia em TS (molde: `figurino_producao_read.py:80`, `status_labels`). |
| II. Padrões de código | Type hints e docstrings Google; funções ≤ ~30 linhas; constantes em `app/constants.py` (`FORM_CLOSE_REASON_*`, janelas de dias, corte padrão); `except` sempre com log; TS estrito, sem `any`; `ruff check` nos tocados e `ruff format` só nos módulos novos (`destino_ops.py`, `pre_evento_ops.py`). |
| III. Camadas / API First | Núcleo em `app/formularios/{formularios_ops,destino_ops,pre_evento_ops}.py`, sem `flask.request`. Endpoints nos módulos já registrados `formularios_admin_{read,write}.py`, só com RBAC e serialização. `dashboard_service` só chama o núcleo dentro de `_bloco`. `_link_form_response` (`calendar/routes.py:3611`) delega ao núcleo em vez de escrever à mão. Sem Jinja novo. |
| IV. Não quebrar o que funciona | A migration é aditiva e nullable. As contagens mudam de forma na Home e na tela Formulários **no mesmo commit**, porque `FormulariosSummary = StatusCounts`. Filtro antigo cai em "todos" sem erro. O automático continua destravado. A mudança de 409 em `vincular-evento` foi conferida: a tela nunca oferece ligar formulário já ligado. Consumidores conferidos: `FormResponsePicker`, `ClientDetailPage.form_history`, `ComercialSection`, `EventEditPage`. **Portão "campo novo do payload é opcional no React"**: os campos novos entram opcionais nos tipos e são lidos com fallback (`?.`, `?? 0`, `[]`), porque servidor e site sobem separados e ficam ~1 min em versões diferentes em todo deploy. A troca de forma das contagens vai num commit só, com os consumidores (US1). |
| V. UI/UX com feedback | Toda ação nova é mutation do TanStack com botão em estado de carregamento. Todo erro aparece inline em pt-BR (o app interno não tem toast), e o 409 também invalida a lista. Encerrar com "Outro" sem frase aponta e foca o campo. "Não é este" pede confirmação (`ConfirmDialog`). Na data suspeita, o Salvar **nunca** fica desabilitado: o envio marca o campo com `setError` e o efeito de foco existente (`EventCreatePage.tsx:265-275`) leva até ele. Os blocos do cadastro preenchido mostram a marca "do formulário" e os alertas no campo. |
| VI. Esteira (Nível 1) | Migration, endpoints novos, três telas e três domínios (formulários, agenda, notificações): esteira completa, com os artefatos em `specs/298-formulario-vira-evento/`. |
| VII. Living Spec | A spec foi esclarecida em 10/09 (4 respostas) e em 11/09 (3 respostas ao checklist e 5 decisões sobre a análise) antes das tarefas. Qualquer desvio no implement volta primeiro para a `spec.md`. |
| VIII. Verify antes do núcleo | `verify_298.py` fica na fase Foundational do `tasks.md`, escrito antes dos núcleos e falhando pelos motivos certos. Tem 17 linhas (1–13, 14a, 14b, 15, 16): escrita conferida por conexão separada; o cenário 15 exige exatamente 403 para CASTING e FINANCEIRO, com o COMERCIAL em 200 como controle; e o Google fica fora (chamada falsa em `insert_event`). |
| IX. Dinheiro BRL | Não toca em valores. O cadastro preenchido não traz valor de venda. |
| X. Mobile-first público | Não se aplica: o formulário público não muda (fora de escopo). |
| XI. Framer Motion | A expansão da linha repetida, a faixa de sugestão e a **saída da linha resolvida** (`AnimatePresence`) usam `motion` com `useReducedMotion`, no padrão de `ListaTruncada` (`DashboardPage.tsx:193-224`), com 150–350 ms. O dono aceita sem animação onde ela não for possível. |
| XII. Combobox / Maps | O motivo tem 5 opções, então `<select>` nativo é permitido. O endereço preenchido entra no `GoogleAddressInput` existente como valor inicial; nenhuma busca nova de Maps. |
| XIII. RBAC declarado | Encerrar, reabrir, repetidos e sugestão: `_require_vendas`. Dados para evento e `POST /api/events`: `_can_create_event`. Home: gate atual. Tabela em [contracts/api-formularios.md](./contracts/api-formularios.md) e linhas novas em `docs/01` §4.3. |
| XIV. Config / efeito externo | Nenhuma env nova. O corte tem default real (`CORTE_FORMULARIOS_PADRAO`). Nenhuma escrita externa nova, e a guarda 409 **reduz** o risco de evento duplicado no Google. |
| Stack | Migration à mão com `down_revision = "c9f4a2b71e60"` (head único conferido). `flask db migrate` não é usado. Sem segredo. |
| Operação e Deploy | Não toca `startCommand`. Migration aditiva, sem ensaio destrutivo. Pós-deploy: CLI `formularios-avisos-resolvidos` com dry-run e depois `--execute` no `manto-backend`, com `MANTO_SEM_THREADS=1` ([quickstart.md](./quickstart.md) §4). |

**Resultado do gate**: aprovado, sem violação a justificar. Reavaliado após a Phase 1, com os
contratos, o modelo de dados e o quickstart escritos: continua aprovado.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/298-formulario-vira-evento/
├── spec.md              # /speckit-specify + /speckit-clarify (10/09)
├── plan.md              # este arquivo
├── research.md          # Phase 0 — R1..R28
├── data-model.md        # Phase 1 — colunas, tabela, estados, linha da Home
├── quickstart.md        # Phase 1 — verify, telas, pós-deploy
├── contracts/
│   ├── api-formularios.md       # endpoints novos e alterados, RBAC, CLI
│   ├── dashboard-formularios.md # bloco formularios do /api/dashboard e consumo no React
│   └── pre-evento.md            # formato do para-evento e mapa campo → evento
├── checklists/{requirements,revisao}.md
├── tasks.md             # /speckit-tasks
└── verify_298.py        # Princípio VIII — escrito antes do núcleo
```

### Código (caminhos reais)

```text
migrations/versions/<rev>_formulario_destino.py      # aditiva: 4 colunas, tabela de descartes, índice parcial
app/models.py                                        # FormResponse (+colunas, __table_args__), FormResponseDismissedEvent
app/constants.py                                     # CORTE_FORMULARIOS_PADRAO, FORM_CLOSE_REASON_*, janelas
app/formularios/formularios_ops.py                   # corte_de_chegada, _status_condition/count_status/list_responses por destino,
                                                     #   apply_event_link (núcleo: cliente 2 sentidos, limpa encerramento, sino),
                                                     #   _attempt_auto_link/retry pelo núcleo, retry sem encerrados, link_event 409
app/formularios/destino_ops.py            (novo)     # listar_sem_destino (grupos, severidade, repetidos, sugestões), encerrar,
                                                     #   reabrir (com audit()), manter_entre_repetidos, confirmar/descartar sugestão,
                                                     #   usar_cliente_do_evento
app/formularios/pre_evento_ops.py         (novo)     # extrair_para_evento + sinônimos + parse de hora/período + pagamento
app/notificacoes/notificacoes_ops.py                 # marcar_lidas_por_entidade; notificar_resposta_formulario não emite se já ligado
app/api/formularios_admin_read.py                    # filtros novos, resumo (+destino, encerramento, fuso), detalhe (+sugestão, flags), para-evento
app/api/formularios_admin_write.py                   # encerrar, reabrir, manter-entre-repetidos, sugestão confirmar/descartar,
                                                     #   usar-cliente-do-evento; vincular 409
app/api/dashboard_service.py                         # bloco formularios → destino_ops (dentro de _bloco)
app/api/agenda_write.py                              # POST /api/events: 409 antes do Google se o formulário já tem evento
app/calendar/routes.py                               # _link_form_response delega a apply_event_link e levanta FormularioJaTemDestino
app/calendar/event_ops.py                            # update_event_core e set_event_form_response: 409 quando o formulário é de outro evento
app/api/formularios_write.py                         # envio público: sem aviso se já nasce ligado
app/cli.py                                           # flask formularios-avisos-resolvidos e formularios-cliente-do-evento [--execute]
frontend/apps/internal/src/lib/formulariosAdmin.ts   # tipos novos, hooks das ações, invalidarDestinoDeFormulario
frontend/apps/internal/src/lib/notificacoes.ts       # exporta invalidarNotificacoes
frontend/apps/internal/src/lib/types.ts              # FormulariosSummary próprio (linhas + contagens)
frontend/apps/internal/src/lib/eventCreate.ts, eventInline.ts  # invalidações ao criar, editar e ligar pela aba Comercial
frontend/apps/internal/src/pages/DashboardPage.tsx   # painel "Formulários sem evento na agenda" e FormularioSemDestinoRow
frontend/apps/internal/src/components/formularios/EncerrarFormularioDialog.tsx  (novo)
frontend/apps/internal/src/pages/FormulariosAdminPage.tsx      # cartões por destino, selo "Encerrado", seção Destino, sugestão
frontend/apps/internal/src/pages/EventCreatePage.tsx # consome para-evento: preenche, marca, alertas, evento existente
frontend/apps/internal/src/components/EventFormBlocks/*.tsx, ClientPicker.tsx  # props opcionais de origem/alerta; quick create com valor inicial
```

**Decisão de estrutura**:
- `formularios_ops.py` já tem mais de 800 linhas e é o dono do vínculo, então fica com o que é
  **vínculo e contagem** (corte, partições, núcleo).
- O que é **tarefa da comercial** (lista, encerramento, sugestão) vai para `destino_ops.py`.
- A **tradução formulário → evento** vai para `pre_evento_ops.py`.
- Os três ficam em `app/formularios/`, e os endpoints nos módulos já registrados em
  `app/api/__init__.py`.
- O componente de diálogo de encerramento é o único arquivo novo do front, porque é usado na Home e
  na tela Formulários.

## Sequência de implementação (blocos commitáveis)

1. **Foundational.** O `verify_298.py` falha pelos motivos certos. Migration, modelos e constantes.
   `flask db upgrade` no `manto_local`.
2. **Núcleo de vínculo.**
   - Corte e partições em `count_status` e `list_responses`.
   - `apply_event_link` estendido, com `marcar_lidas_por_entidade`.
   - Os três caminhos pelo núcleo; `retry` sem encerrados; `link_event` 409.
   - Guarda 409 no `POST /api/events`; aviso não emitido quando o formulário nasce ligado.
   - Cenários 10 e 14a.
3. **Destino.** `destino_ops`: lista, encerrar, reabrir (com `audit()`), repetidos, sugestão e "usar a
   cliente do evento", com os endpoints. Cenários 1–8, 13 e 15. A distribuição exata dos cenários por história está no
   `tasks.md`, que prevalece sobre esta lista.
4. **Pré-evento.** `pre_evento_ops` e o endpoint `para-evento`. Cenários 11 e 12.
5. **Home.** Bloco `formularios` novo no dashboard, tipos, painel e linha.
6. **Tela Formulários.** Cartões por destino, selos, seção Destino, sugestão, fuso de "Recebida em".
7. **Criar evento.** Preenchimento, marcas, alertas, cadastro rápido e aviso de evento existente.
8. **Invalidações do front e CLI de avisos resolvidos.**
9. **Portões.** Typecheck, ruff, verify 17/17 e as três telas abertas.
10. **Docs.** `docs/01` (head, endpoints, RBAC §4.3, `form_responses`), `docs/02` (Home,
    Formulários, `/events/new`), `docs/04` (invariante do destino), `docs/05` (limpeza de dados,
    agrupamento por celular sem o 9º dígito), `docs/03` (entrada no topo).

## Riscos e como cada um é contido

| Risco | Contenção |
|---|---|
| Mudar `StatusCounts` quebra a Home e a tela Formulários ao mesmo tempo | Tipos separados (`FormulariosSummary` próprio) e os dois consumidores no mesmo bloco de commits; typecheck das três SPAs |
| Automático pelo núcleo passaria a travar e perderia a religação depois de excluir o evento | Parâmetro `decisao_humana=False` para o automático; cenário 10 confere que o evento excluído devolve o formulário |
| Sync religando formulário encerrado | `retry_auto_link_pending` filtra `closed_at IS NULL`; cenário 14a roda o retry depois de encerrar |
| Evento duplicado no Google por dois cliques ou duas pessoas | O formulário é bloqueado (`SELECT … FOR UPDATE`) antes do Google e fica bloqueado até o commit: a segunda requisição espera e recebe 409. Custo aceito: a linha fica presa durante a chamada ao Google (~1 s). O botão fica em estado de envio. A rota Jinja de criação fica fora, porque `/events` não passa pelo `server.js` |
| Metade dos formulários desde junho (carga WhatsForm) sem preenchimento | Mapa de sinônimos dos dois vocabulários; cenário 11 com um formulário de cada |
| Parse de período errado grava um horário falso | Só formas inequívocas; o resto fica vazio com o texto, e o fim é obrigatório no cadastro |
| Divergência de cliente mexendo no evento | O núcleo não acrescenta "Outros" quando as duas existem e diferem; devolve `divergencia_cliente` |
| Painel novo falhar em silêncio (`_bloco` esconde) | O verify confere que `formularios` veio preenchido para COMERCIAL |
| Celular antigo sem o 9º dígito não agrupa | Aceito; registrado em `docs/05` |
| Verify escrever no calendário real | Semeia direto no banco. Dentro do processo, troca `app.calendar.routes.insert_event` por uma chamada falsa que falha se for chamada (a view importa a função na hora, `agenda_write.py:740`). Todo evento de teste leva "[TESTE verify 298] pode apagar" no título (R15) |
| Site e servidor em versões diferentes no deploy | Campos novos opcionais no React, lidos com fallback |
| Cliente e ficha perdendo dados no envio público | `attempt_auto_link_client` roda antes do vínculo automático, preservando `auto_phone` e o `fill_client_from_response` (R22) |

## Rastreamento de complexidade

Nenhuma violação do Constitution Check a justificar.
