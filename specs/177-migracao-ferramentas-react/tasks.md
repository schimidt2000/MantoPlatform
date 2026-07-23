# Tasks: Migração das últimas ferramentas Jinja para React

**Input**: Design documents from `specs/177-migracao-ferramentas-react/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md, quickstart.md

**Tests**: não solicitados explicitamente no spec — a verificação funcional (script de test
client Flask contra `manto_local`) cobre o papel de teste de integração, mesmo padrão de todas
as fatias 145-176.

**Rotas React novas** (registradas em `frontend/apps/internal/src/App.tsx`):
`/gastos`, `/gastos/recorrentes`, `/orcamento`, `/orcamento/historico`,
`/orcamento/configuracoes`, `/casting/avaliacoes` (não usar `/talents/avaliacoes` — colidiria
com a rota existente `/talents/:id`), `/formularios`, `/formularios/:id`,
`/formularios/editor/:formType`.

## Phase 1: Setup

- [ ] T001 Ler `app/gastos/routes.py`, `app/talents/routes.py:262-559`,
  `app/formularios/routes.py:525-813`, `app/orcamento/routes.py` por inteiro, e as seções
  correspondentes de `app/models.py` para confirmar o shape exato de cada `to_dict()`/resposta
  hoje renderizada em Jinja antes de escrever qualquer API nova (nenhuma mudança de
  comportamento esperada, só de camada). Conferir também quem mais importa
  `ensure_recurring_entries()`/`recurring_alerts()` (`app/gastos/routes.py:357,395`) antes de
  movê-las.

## Phase 2: Foundational

- [ ] T002 [P] Confirmar em `specs/144-migracao-react-spa/contracts/api-conventions.md` o
  envelope de erro/sucesso e revisar um exemplo recente de RBAC-como-função (ex.
  `app/api/educamanto_write.py`) para replicar o mesmo estilo nos 4 domínios novos desta
  feature.
- [ ] T003 Confirmar em `frontend/apps/internal/src/App.tsx` o padrão de registro de rota e em
  `frontend/apps/internal/src/lib/navigation.tsx` a estrutura de `SECTIONS`/`buildNavSections()`
  — nenhuma mudança ainda, só levantamento para evitar retrabalho nas 7 fatias seguintes.

**Checkpoint**: convenções confirmadas — pronto para implementar as 7 user stories, cada uma
independente (domínios de `*_ops.py` diferentes, sem dependência de código entre elas).

---

## Phase 3: User Story 1 — Gerenciar Gastos Extras sem sair da SPA (P1) 🎯 MVP

**Goal**: usuário do Financeiro registra/filtra/aprova/rejeita/exclui/vincula gasto extra a
evento, tudo em React.

**Independent Test**: criar um gasto, aprovar/rejeitar outro, vincular um terceiro a um evento —
sem depender de nenhuma outra user story.

- [ ] T004 [US1] Extrair `app/gastos/gastos_ops.py`: funções puras
  `list_expenses(user, filters) -> list[SpecialExpense]`, `create_expense(user, data: dict, receipt_file) -> SpecialExpense`,
  `approve_expense(expense) -> SpecialExpense`, `reject_expense(expense, reason: str) -> SpecialExpense`,
  `delete_expense(expense) -> None`, `link_expense_to_event(expense, event_id: int | None) -> SpecialExpense`
  — mesma lógica hoje inline em `index()`/`novo()`/`aprovar()`/`rejeitar()`/`excluir()`/
  `vincular_evento()` de `app/gastos/routes.py:80-280`, incluindo `_save_receipt`/`_resolve_event_id`/`_log`
  (movidos para o módulo). Sem `flask.request`/`render_template` dentro do módulo.
- [ ] T005 [US1] Atualizar `app/gastos/routes.py` (rotas de gasto extra) para chamar
  `gastos_ops.py` em vez de conter a lógica inline — zero mudança de comportamento.
- [ ] T006 [US1] `app/api/gastos_read.py` (novo): `GET /api/gastos` (RBAC: autenticado, SUPERADMIN
  vê todos, demais só os próprios) e `GET /api/gastos/eventos` (busca de eventos para o
  seletor de vínculo).
- [ ] T007 [US1] `app/api/gastos_write.py` (novo): `POST /api/gastos` (multipart, comprovante),
  `POST /api/gastos/<id>/aprovar`, `POST /api/gastos/<id>/rejeitar` (RBAC SUPERADMIN, 409 se já
  não `pendente`), `DELETE /api/gastos/<id>`, `POST /api/gastos/<id>/vincular-evento`.
- [ ] T008 [P] [US1] `frontend/apps/internal/src/lib/gastos.ts` (novo): hooks
  `useGastosExtras(filters)`, `useGastosEventos()`, `useCreateGasto()`, `useApproveGasto()`,
  `useRejectGasto()`, `useDeleteGasto()`, `useLinkGastoEvento()` (TanStack Query, invalidação de
  `["gastos-extras"]`).
- [ ] T009 [US1] `frontend/apps/internal/src/pages/GastosExtrasPage.tsx` (novo): `AppLayout` +
  `PageHeader` + `DenseCard`, lista filtrável (status/categoria/período), formulário de criação
  (upload de comprovante via `FileUpload`, valor via `@manto/money`), ações aprovar/rejeitar
  (SUPERADMIN) e excluir/vincular a evento com `window.confirm` antes de excluir; loading/erro/
  sucesso em toda ação.
- [ ] T010 [US1] Registrar `<Route path="/gastos" element={<GastosExtrasPage />} />` em
  `frontend/apps/internal/src/App.tsx`; em `frontend/apps/internal/src/lib/navigation.tsx`,
  trocar o item `gastos-extras` (linhas ~98-106) de `external: true`/`hint` para rota real com
  `isActive` correto.
- [ ] T011 [US1] Verificação funcional (script contra `manto_local`): criar gasto (201), listar
  (200, escopo próprio vs. SUPERADMIN), aprovar/rejeitar (200 SUPERADMIN, 403 outros papéis, 409
  dupla ação), excluir (204), vincular/desvincular evento (200); paridade confirmada em
  `/gastos/` (Jinja) sem regressão.

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 4: User Story 2 — Calcular e enviar orçamento de show sem sair da SPA (P2)

**Goal**: usuário comercial preenche elenco/horas/transporte/show e recebe o cálculo em React.

**Independent Test**: preencher o formulário de orçamento e conferir que o resultado bate com a
tela clássica para os mesmos parâmetros.

- [ ] T012 [US2] Extrair `app/orcamento/quote_ops.py`: quebrar `_process_quote()`
  (`app/orcamento/routes.py:163-583`, ~420 linhas) em funções ≤30 linhas cada
  (`calculate_quote(payload: dict) -> dict`, mais helpers privados por seção — elenco, horas,
  transporte, show), chamando `pricing.py`/`transport.py` já existentes sem alteração. Também
  extrair `personagens_no_dia(date) -> list[dict]` (hoje `personagens-no-dia`, routes.py:102-105).
- [ ] T013 [US2] Atualizar `app/orcamento/routes.py` (rota `/orcamento/`) para chamar
  `quote_ops.calculate_quote()` em vez da lógica inline — zero mudança de comportamento.
- [ ] T014 [US2] `app/api/orcamento_read.py` (novo): `GET /api/orcamento/personagens-no-dia`,
  `GET /api/orcamento/distancia` (RBAC COMERCIAL/SUPERADMIN, `_require_vendas` replicado como
  função).
- [ ] T015 [US2] `app/api/orcamento_write.py` (novo): `POST /api/orcamento/calcular` (RBAC idem,
  400 com `fields` em validação), `POST /api/orcamento/salvar` (cria `OrcamentoHistory`).
- [ ] T016 [P] [US2] `frontend/apps/internal/src/lib/orcamento.ts` (novo): hooks
  `usePersonagensNoDia(date)`, `useDistancia(endereco)`, `useCalcularOrcamento()`,
  `useSalvarOrcamento()`.
- [ ] T017 [US2] `frontend/apps/internal/src/pages/OrcamentoCalculadoraPage.tsx` (novo):
  formulário react-hook-form + zod (elenco, horas, transporte, show), resultado exibido inline
  (sem navegação de página), ação "Salvar orçamento" chamando `useSalvarOrcamento()`.
- [ ] T018 [US2] Registrar `<Route path="/orcamento" element={<OrcamentoCalculadoraPage />} />`;
  em `navigation.tsx`, trocar o item `calc-orcamento` (linhas ~271-280) de `external`/`hint` para
  rota real.
- [ ] T019 [US2] Verificação funcional: `POST /calcular` com parâmetros de um caso conhecido da
  tela clássica batendo valor a valor; `POST /salvar` gerando registro; RBAC (403 fora de
  COMERCIAL/SUPERADMIN); paridade em `/orcamento/` (Jinja).

**Checkpoint**: US1 + US2 completas.

---

## Phase 5: User Story 3 — Gerenciar Gastos Recorrentes sem sair da SPA (P3)

**Goal**: Financeiro cadastra/administra despesas recorrentes e suas parcelas em React.

**Independent Test**: criar despesa recorrente, gerar/pagar uma parcela, reabri-la.

- [ ] T020 [US3] Estender `app/gastos/gastos_ops.py` (mesmo módulo da US1, mesmo domínio):
  `list_recurring(filters) -> list[RecurringExpense]`, `create_recurring(data: dict) -> RecurringExpense`,
  `update_recurring(rec, data: dict) -> RecurringExpense`, `toggle_recurring(rec) -> RecurringExpense`,
  `delete_recurring(rec) -> None`, `fill_entry(entry, data: dict) -> RecurringExpenseEntry`,
  `skip_entry(entry) -> RecurringExpenseEntry`, `pay_entry(entry) -> RecurringExpenseEntry`,
  `reopen_entry(entry) -> RecurringExpenseEntry`, `delete_entry(entry) -> None` — mesma lógica de
  `app/gastos/routes.py:514-882`, incluindo mover `ensure_recurring_entries()`/
  `recurring_alerts()`/`_parse_conta_form()`/`_parse_programado_form()` preservando assinatura
  pública para os outros callers já identificados em T001.
- [ ] T021 [US3] Atualizar `app/gastos/routes.py` (rotas de recorrentes) para chamar
  `gastos_ops.py` — zero mudança de comportamento; ajustar imports de quem mais chamava
  `ensure_recurring_entries()`/`recurring_alerts()` para o novo caminho.
- [ ] T022 [US3] Estender `app/api/gastos_read.py`: `GET /api/gastos/recorrentes` (RBAC
  FINANCEIRO/SUPERADMIN) retornando contas + parcelas do mês + alertas.
- [ ] T023 [US3] Estender `app/api/gastos_write.py`: `POST /api/gastos/recorrentes`,
  `PATCH /api/gastos/recorrentes/<id>`, `POST /api/gastos/recorrentes/<id>/toggle`,
  `DELETE /api/gastos/recorrentes/<id>`, `POST /api/gastos/recorrentes/entry/<id>/preencher|pular|pagar|reabrir`,
  `DELETE /api/gastos/recorrentes/entry/<id>` (409 em transição de status inválida).
- [ ] T024 [P] [US3] Estender `frontend/apps/internal/src/lib/gastos.ts`: hooks
  `useGastosRecorrentes()`, `useCreateRecorrente()`, `useUpdateRecorrente()`,
  `useToggleRecorrente()`, `useDeleteRecorrente()`, `useFillEntry()`, `useSkipEntry()`,
  `usePayEntry()`, `useReopenEntry()`, `useDeleteEntry()`.
- [ ] T025 [US3] `frontend/apps/internal/src/pages/GastosRecorrentesPage.tsx` (novo): lista de
  contas por tipo, alertas do mês, formulário de criação (campos condicionais por
  `expense_type`), ações de parcela (pagar/pular/reabrir/excluir com confirmação).
- [ ] T026 [US3] Registrar `<Route path="/gastos/recorrentes" element={<GastosRecorrentesPage />} />`;
  em `navigation.tsx`, trocar o item `gastos-recorrentes` (linhas ~256-265).
- [ ] T027 [US3] Verificação funcional: CRUD de recorrente e ações de parcela (200/201/204/409),
  RBAC (403 fora de FINANCEIRO/SUPERADMIN), paridade em `/gastos/recorrentes` (Jinja).

**Checkpoint**: US1 + US2 + US3 completas.

---

## Phase 6: User Story 4 — Consultar histórico de orçamentos e baixar PDF (P4)

**Goal**: usuário comercial revisita orçamentos salvos, baixa PDF, reenvia por e-mail.

**Independent Test**: abrir o histórico, ver detalhe de um orçamento salvo (incluindo um
registro legado), baixar o PDF.

- [ ] T028 [US4] Estender `app/orcamento/quote_ops.py` (mesmo módulo da US2): mover
  `_legacy_quote(entry)` (`app/orcamento/routes.py:595-631`) para função pública
  `legacy_quote(entry) -> dict`, reusada por Jinja e API.
- [ ] T029 [US4] Atualizar `app/orcamento/routes.py` (rotas de histórico/PDF/e-mail) para chamar
  `quote_ops.legacy_quote()` — zero mudança de comportamento.
- [ ] T030 [US4] Estender `app/api/orcamento_read.py`: `GET /api/orcamento/historico` (RBAC
  COMERCIAL vê só o próprio, SUPERADMIN vê todos — mesma regra de `is_sa` em
  `routes.py:714`), `GET /api/orcamento/historico/<id>` (aplica `legacy_quote` quando
  necessário), `GET /api/orcamento/historico/<id>/pdf` (bytes via
  `app/orcamento/pdf.py:gerar_orcamento_pdf`, sem alteração).
- [ ] T031 [US4] Estender `app/api/orcamento_write.py`: `POST /api/orcamento/historico/<id>/enviar-email`
  (reusa o serviço de e-mail já usado por outras áreas), `DELETE /api/orcamento/historico/<id>`.
- [ ] T032 [P] [US4] Estender `frontend/apps/internal/src/lib/orcamento.ts`: hooks
  `useOrcamentoHistorico(filters)`, `useOrcamentoDetalhe(id)`, `useOrcamentoPdf(id)` (via
  `apiFetchBlob`, mesmo padrão da feature 160), `useEnviarEmailOrcamento()`,
  `useDeleteOrcamentoHistorico()`.
- [ ] T033 [US4] `frontend/apps/internal/src/pages/OrcamentoHistoricoPage.tsx` (novo): lista
  filtrável (texto/período), detalhe de um registro (inclusive legado), botão de download de PDF
  e de reenvio por e-mail, exclusão com confirmação.
- [ ] T034 [US4] Registrar `<Route path="/orcamento/historico" element={<OrcamentoHistoricoPage />} />`;
  em `navigation.tsx`, trocar o item `orcamentos` (linhas ~291-300).
- [ ] T035 [US4] Verificação funcional: listar/filtrar, detalhe de registro atual e legado
  (mesmos campos que o Jinja), PDF batendo com `gerar_orcamento_pdf` chamado direto, envio de
  e-mail (mock do serviço), exclusão, RBAC (dono vs. SUPERADMIN vs. 403 fora de
  COMERCIAL/SUPERADMIN), paridade em `/orcamento/historico` (Jinja).

**Checkpoint**: US1-US4 completas.

---

## Phase 7: User Story 5 — Configurar preços da calculadora sem sair da SPA (P5)

**Goal**: administrador ajusta valores de referência da Calculadora de Orçamento em React.

**Independent Test**: alterar um valor de referência e conferir que a próxima simulação (US2)
reflete a mudança.

- [ ] T036 [US5] Estender `app/api/orcamento_read.py`: `GET /api/orcamento/settings` (RBAC
  SUPERADMIN, `_require_superadmin` replicado como função) — adapter fino sobre
  `app/orcamento/settings.py:load()`, sem alteração ao módulo existente.
- [ ] T037 [US5] Estender `app/api/orcamento_write.py`: `POST /api/orcamento/settings` (chama
  `settings.save()`), `POST /api/orcamento/settings/especiais`,
  `DELETE /api/orcamento/settings/especiais/<nome>` (usa `especiais_list()` existente).
- [ ] T038 [P] [US5] Estender `frontend/apps/internal/src/lib/orcamento.ts`: hooks
  `useOrcamentoSettings()`, `useSaveOrcamentoSettings()`, `useAddEspecial()`,
  `useRemoveEspecial()`.
- [ ] T039 [US5] `frontend/apps/internal/src/pages/OrcamentoConfigPrecosPage.tsx` (novo):
  formulário por categoria (ator/cantor/técnico/coordenador/maquiador), lista de itens especiais
  (adicionar/remover), tipos de acréscimo — todos os campos monetários via `@manto/money`;
  visível só a SUPERADMIN (acesso negado amigável para os demais).
- [ ] T040 [US5] Registrar `<Route path="/orcamento/configuracoes" element={<OrcamentoConfigPrecosPage />} />`;
  em `navigation.tsx`, trocar o item `config-precos` (linhas ~281-290).
- [ ] T041 [US5] Verificação funcional: `GET`/`POST /settings` (200 SUPERADMIN, 403 outros),
  alterar valor e confirmar reflexo em `POST /orcamento/calcular` (US2, FR-011),
  adicionar/remover item especial, paridade em `/orcamento/settings` (Jinja).

**Checkpoint**: US1-US5 completas — domínio "Ferramentas/Orçamento" 100% em React.

---

## Phase 8: User Story 6 — Avaliar elenco de um evento sem sair da SPA (P6)

**Goal**: usuário com acesso a Casting consulta avaliações e distribuição de notas, alterna modo
anônimo.

**Independent Test**: filtrar por evento/período/categoria e conferir que a distribuição de
notas bate com a tela clássica para os mesmos filtros.

- [ ] T042 [US6] Criar `app/talents/rating_ops.py` (novo, não confundir com `talent_ops.py`
  existente): `list_ratings(filters: dict, viewer_is_superadmin: bool) -> list[dict]`,
  `rating_distribution(ratings) -> dict`, `resolve_author(rating, viewer_is_superadmin) -> str | None`,
  `set_anonymous_mode(enabled: bool) -> None` — mesma lógica hoje inline em
  `avaliacoes()`/`toggle_modo_anonimo()` (`app/talents/routes.py:262-559`), incluindo a resolução
  de papel do autor via `strip_role_prefix` (`app.calendar.routes`).
- [ ] T043 [US6] Atualizar `app/talents/routes.py` (rota `/talents/avaliacoes`) para chamar
  `rating_ops.py` — zero mudança de comportamento.
- [ ] T044 [US6] `app/api/ratings_read.py` (novo): `GET /api/ratings` (RBAC autenticado, filtros
  `event_id`/`category`/`date_from`/`date_to`, aplica `resolve_author` conforme modo anônimo e
  papel do requisitante).
- [ ] T045 [US6] `app/api/ratings_write.py` (novo): `POST /api/ratings/modo-anonimo` (RBAC
  SUPERADMIN, grava `SiteSetting.ratings_fully_anonymous`).
- [ ] T046 [P] [US6] `frontend/apps/internal/src/lib/ratings.ts` (novo): hooks
  `useRatings(filters)`, `useToggleAnonymousMode()`.
- [ ] T047 [US6] `frontend/apps/internal/src/pages/AvaliacaoCastingPage.tsx` (novo): filtros
  (evento/período/categoria), distribuição de notas por categoria, lista de avaliações, toggle
  de modo anônimo (visível só a SUPERADMIN).
- [ ] T048 [US6] Registrar `<Route path="/casting/avaliacoes" element={<AvaliacaoCastingPage />} />`
  (não usar `/talents/avaliacoes` — colidiria com a rota existente `/talents/:id`); em
  `navigation.tsx`, trocar o item `avaliacao-casting` (linhas ~120-129), atualizando o `href`
  interno também.
- [ ] T049 [US6] Verificação funcional: filtros retornando o mesmo subconjunto que a tela
  clássica, distribuição de notas correta, modo anônimo omitindo autor para não-SUPERADMIN e
  visível para SUPERADMIN, toggle restrito a SUPERADMIN (403 outros), paridade em
  `/talents/avaliacoes` (Jinja).

**Checkpoint**: US1-US6 completas.

---

## Phase 9: User Story 7 — Gerenciar respostas de Formulários (Comercial) sem sair da SPA (P7)

**Goal**: usuário comercial revisa/associa/vincula/exclui respostas de formulário e edita a
definição de campos.

**Independent Test**: abrir uma resposta existente, associá-la a cliente e evento, editar um
campo do formulário.

- [ ] T050 [US7] Criar `app/formularios/formularios_ops.py` (novo): `search_responses(filters: dict) -> list[FormResponse]`,
  `get_response(id: int) -> FormResponse`, `associate_client(response, client_id: int) -> FormResponse`,
  `dissociate_client(response) -> FormResponse`, `link_event(response, event_id: int) -> FormResponse`,
  `unlink_event(response) -> FormResponse`, `delete_response(response) -> None`,
  `list_field_definitions(form_type: str) -> list[FormFieldDefinition]`,
  `create_field(form_type: str, data: dict) -> FormFieldDefinition`,
  `update_field(field, data: dict) -> FormFieldDefinition` (bloqueia alteração de
  `field_type`/`field_key` quando `is_system=True`), `move_field(field, direction: str) -> None`,
  `delete_field(field) -> None` (bloqueia quando `is_system=True`) — mesma lógica hoje inline em
  `app/formularios/routes.py:525-813`, incluindo `_fill_client_from_response`/`_attempt_auto_link`
  (marcam `event_link_source`/`event_link_locked` exatamente como hoje).
- [ ] T051 [US7] Atualizar `app/formularios/routes.py` (rotas staff — NÃO tocar as rotas públicas
  `/f/*`) para chamar `formularios_ops.py` — zero mudança de comportamento.
- [ ] T052 [US7] `app/api/formularios_admin_read.py` (novo — nome distinto de
  `formularios_write.py` público): `GET /api/formularios/respostas` (RBAC COMERCIAL/FINANCEIRO/
  SUPERADMIN), `GET /api/formularios/respostas/<id>`, `GET /api/formularios/editor/<form_type>`
  (RBAC SUPERADMIN).
- [ ] T053 [US7] `app/api/formularios_admin_write.py` (novo): `POST /api/formularios/respostas/<id>/associar|desassociar|vincular-evento|desvincular-evento`,
  `DELETE /api/formularios/respostas/<id>` (RBAC SUPERADMIN),
  `POST /api/formularios/editor/<form_type>/campo`, `PATCH /api/formularios/editor/campo/<id>`,
  `POST /api/formularios/editor/campo/<id>/mover`, `DELETE /api/formularios/editor/campo/<id>`
  (RBAC SUPERADMIN, 400/403 em campo `is_system`).
- [ ] T054 [P] [US7] `frontend/apps/internal/src/lib/formulariosAdmin.ts` (novo): hooks
  `useFormResponses(filters)`, `useFormResponse(id)`, `useAssociateClient()`,
  `useDissociateClient()`, `useLinkEvent()`, `useUnlinkEvent()`, `useDeleteFormResponse()`,
  `useFormFieldDefinitions(formType)`, `useCreateField()`, `useUpdateField()`, `useMoveField()`,
  `useDeleteField()`.
- [ ] T055 [US7] `frontend/apps/internal/src/pages/FormulariosAdminPage.tsx` (novo): lista/busca
  de respostas, ação associar/desassociar cliente e vincular/desvincular evento; editor de
  campos inline por `form_type` (adicionar/mover/excluir, campo `is_system` sem botão de
  excluir/editar tipo), exclusão de resposta restrita a SUPERADMIN com confirmação.
- [ ] T056 [US7] Registrar `<Route path="/formularios" element={<FormulariosAdminPage />} />` (e
  sub-rotas `/formularios/:id`, `/formularios/editor/:formType` se a tela optar por rotas
  separadas em vez de estado interno); em `navigation.tsx`, trocar o item `formularios` (linhas
  ~224-234).
- [ ] T057 [US7] Verificação funcional: busca/filtros, associar/desassociar cliente, vincular/
  desvincular evento (conferir `event_link_locked=true` após ação manual), exclusão restrita a
  SUPERADMIN, editor de campos (criar/editar/mover/excluir campo comum; 400/403 em campo
  `is_system`), paridade em `/formularios/` (Jinja).

**Checkpoint**: as 7 user stories completas — spec 177 encerrada, zero item `external: true`
restante em `navigation.tsx` para essas áreas.

---

## Phase 10: Polish & Cross-Cutting

- [ ] T058 [P] `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal` sem erros.
- [ ] T059 [P] `ruff check` nos arquivos Python novos/tocados (`gastos_ops.py`, `rating_ops.py`,
  `formularios_ops.py`, `quote_ops.py`, `app/api/gastos_*.py`, `app/api/ratings_*.py`,
  `app/api/formularios_admin_*.py`, `app/api/orcamento_*.py`, e os 4 `routes.py` tocados);
  `ruff format` só nos arquivos novos.
- [ ] T060 Conferir `frontend/apps/internal/src/lib/navigation.tsx` inteiro: confirmar que
  nenhum item das 7 áreas restou com `external: true` (SC-001) e que todos usam `isActive` real.
- [ ] T061 Conferir as 7 telas em viewport desktop e mobile (375px) antes de "pronto"; confirmar
  transições Framer Motion e `useReducedMotion()` nas listas/filtros novos.
- [ ] T062 Confirmar zero regressão nas 7 rotas Jinja legadas (paridade final, estratégia
  strangler-fig — nenhuma delas é removida nesta feature).
- [ ] T063 Atualizar `docs/changelog.html` com a entrega (linguagem simples, o que mudou) e
  republicar no mesmo link já existente.

## Dependencies & Execution Order

- **Setup (T001) → Foundational (T002-T003)**: levantamento de convenções, não bloqueiam
  execução paralela das user stories, mas devem ser lidos antes de escrever qualquer API.
- **US1 (T004-T011)**: depende só do Foundational — MVP, entregável isoladamente.
- **US2 (T012-T019)**: depende só do Foundational — independente de US1.
- **US3 (T020-T027)**: mesmo módulo `gastos_ops.py` de US1 (T004) — na prática, implementar
  depois de US1 para evitar conflito de edição simultânea do mesmo arquivo.
- **US4 (T028-T035)**: mesmo módulo `quote_ops.py` de US2 (T012) — implementar depois de US2
  pelo mesmo motivo; também reusa `useOrcamentoPdf`-style pattern já validado em US2.
- **US5 (T036-T041)**: reusa `app/api/orcamento_read.py`/`orcamento_write.py` de US2/US4 (mesmos
  arquivos) — implementar depois de US2 (compartilha o par de módulos de API, não o `quote_ops.py`).
- **US6 (T042-T049)**: totalmente independente das demais (domínio `app/talents`).
- **US7 (T050-T057)**: totalmente independente das demais (domínio `app/formularios`).
- **Polish (T058-T063)**: só depois das 7 user stories.

Ordem sugerida (minimiza conflito de arquivo dentro do mesmo domínio): **US1 → US3 → US2 → US5 →
US4 → US6 → US7** (US6/US7 podem furar a fila e ser feitas a qualquer momento, inclusive em
paralelo com as demais, por não compartilharem nenhum arquivo).

## Parallel Execution Examples

- US6 e US7 podem ser implementadas em paralelo entre si e com qualquer uma das demais — não
  compartilham nenhum arquivo (`app/talents/*` vs. `app/formularios/*`).
- Dentro de cada user story, o hook `lib/<dominio>.ts` (`[P]`) pode ser escrito em paralelo ao
  endpoint de API correspondente, integrando ao final (mesmo padrão de todas as fatias 145-176).
- T058/T059 (tsc/build e ruff) são paralelizáveis entre si na fase de polish.

## Implementation Strategy

**MVP = User Story 1** (T001-T011): Gastos Extras é a ferramenta de uso mais frequente da lista
e fecha sozinha o primeiro item de menu externo. As demais 6 user stories seguem como
incrementos subsequentes no mesmo branch, cada uma verificada e commitada antes da próxima —
dado o volume (7 fatias), commits atômicos por user story são preferíveis a um único commit
gigante, mas o merge final para `main` acontece uma vez, ao fim da feature completa (conforme
preferência já registrada do usuário para o fluxo autônomo de spec-kit).
