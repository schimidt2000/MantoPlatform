---

description: "Task list template for feature implementation"
---

# Tasks: RBAC, edição e "Aprovado com edições" em Gastos Extras

**Input**: Design documents from `/specs/179-gastos-extras-rbac-edicao/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/gastos-api.md,
quickstart.md

**Tests**: não foi pedido TDD explícito nesta feature; a verificação segue o padrão já
obrigatório do projeto (`CLAUDE.md`/constituição): script funcional com Flask test client contra
`manto_local` + Playwright, executados ao final de cada fatia (não antes da implementação).

**Organization**: tarefas agrupadas pelas 3 User Stories da spec.md (US1 = colaborador comum,
US2 = financeiro/superadmin gerencial, US3 = modal de cadastro/edição).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Web app já estabelecida pelo repo: backend em `app/`, frontend em `frontend/apps/internal/src/`.

---

## Phase 1: Setup

- [ ] T001 Confirmar `manto_local` (Postgres) atualizada e no head das migrations:
  `python -m flask db heads` com `DATABASE_URL` apontado via `.\scripts\db\run-local.ps1`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: mudanças de schema e núcleo de negócio compartilhado que TODAS as user stories
precisam. Nenhuma story começa antes desta fase.

- [ ] T002 Criar migration Alembic nova em `migrations/versions/` (`down_revision =
  "d0fdc94beccc"`, estilo de `migrations/versions/a7b8c9d0e1f2_special_expense_disbursement.py`)
  adicionando `special_expenses.approved_with_edits` (`Boolean`, `server_default=sa.false()`,
  `nullable=False`), com `upgrade()`/`downgrade()` completos.
- [ ] T003 Adicionar `approved_with_edits` em `class SpecialExpense` (`app/models.py`, perto de
  `payment_status`/`paid_at_creation`) — `db.Column(db.Boolean, default=False, nullable=False,
  server_default="false")`. `STATUSES` não muda.
- [ ] T004 Aplicar a migration em `manto_local`: `python -m flask db upgrade` com
  `DATABASE_URL` da cópia local; confirmar com `python -m flask db heads`.
- [ ] T005 [P] Extrair `_validate_expense_data(data: dict) -> dict` em
  `app/gastos/gastos_ops.py` a partir da validação hoje embutida em `create_expense`
  (descrição/valor/desembolso), com type hints + docstring; `create_expense` passa a chamá-la
  (sem duplicar a regra).
- [ ] T006 [P] Adicionar `list_expenses_for_admin() -> list[SpecialExpense]` em
  `app/gastos/gastos_ops.py` (todos os gastos, sem filtro, mesma ordenação de `list_expenses`) —
  função nova, não usada pela Jinja.
- [ ] T007 [P] Adicionar `expense_totals(expenses: list[SpecialExpense]) -> dict` em
  `app/gastos/gastos_ops.py`: contagem + soma de `amount` por chave `todos`/`pendente`/
  `aprovado`/`rejeitado`.
- [ ] T008 Adicionar `edit_expense(expense, actor, data, event_id, aprovar: bool) ->
  SpecialExpense` em `app/gastos/gastos_ops.py` (depende de T003, T005): reusa
  `_validate_expense_data`, calcula `changed` comparando os campos editáveis antes de
  sobrescrever, bloqueia `status == "rejeitado"` sem `aprovar=True` (`GastoStateError`), aplica
  `aprovar` (status/approved_by_id/approved_at), seta `approved_with_edits=True` quando o
  resultado final é `"aprovado"` e `changed`, loga via `_log(actor, "gasto", ..., "edit", ...)`.

**Checkpoint**: schema, funções de núcleo prontas — as 3 user stories podem começar.

---

## Phase 3: User Story 1 - Colaborador comum vê e acompanha os próprios gastos (Priority: P1) 🎯 MVP

**Goal**: colaborador sem papel de gestão só vê/gerencia os próprios gastos, com o badge
"Aprovado c/ edições" visível quando aplicável.

**Independent Test**: logar como usuário sem `SUPERADMIN`/`FINANCEIRO`, abrir `/gastos`, ver só
os próprios gastos, sem KPIs; registrar um gasto novo; após um gestor aprová-lo com edição
(via US2), o autor vê "Aprovado c/ edições".

### Implementation for User Story 1

- [ ] T009 [US1] Em `app/api/gastos_read.py`, `_expense_dict`: adicionar
  `"approved_with_edits": e.approved_with_edits`.
- [ ] T010 [US1] Em `app/api/gastos_read.py`, `api_gastos_list`: quando NÃO
  `is_financeiro(current_user)`, manter o comportamento atual (`list_expenses(current_user)`,
  sem `totals`); renomear a chave de resposta `is_superadmin` para `can_manage`
  (`gastos_ops.is_financeiro(current_user)`).
- [ ] T011 [P] [US1] Em `frontend/apps/internal/src/lib/gastos.ts`: adicionar
  `approved_with_edits: boolean` em `GastoExtra`; renomear `is_superadmin` para `can_manage` em
  `GastosExtrasResponse` e adicionar `totals?: {...}` (tipos, sem lógica ainda).
- [ ] T012 [US1] Em `frontend/apps/internal/src/pages/GastosExtrasPage.tsx`: no caminho
  `!can_manage`, exibir "Meus Gastos" com a tabela filtrada pela própria API (sem coluna AUTOR),
  status com 4 rótulos (`Pendente`/`Aprovado`/`Aprovado c/ edições`/`Rejeitado`) usando
  `status === "aprovado" && approved_with_edits` para o 4º rótulo, cor visual distinta.

**Checkpoint**: US1 funcional e testável de forma independente (mesmo sem a tabela/edição do
gestor ainda existir — a leitura já reflete `approved_with_edits` assim que o campo existir no
banco).

---

## Phase 4: User Story 2 - Financeiro/Superadmin gerencia todos os gastos (Priority: P1)

**Goal**: usuários com papel `FINANCEIRO` ou `SUPERADMIN` veem os 4 KPIs, a tabela global, e têm
ações completas (aprovar/rejeitar/editar/vincular evento/excluir), incluindo o fluxo "editar (+
aprovar)" que gera "Aprovado c/ edições".

**Independent Test**: logar como `FINANCEIRO` (sem `SUPERADMIN`), abrir `/gastos`, ver os 4 KPIs
e a tabela completa; aprovar 1 clique; editar+aprovar um pendente com dado alterado e ver
"Aprovado c/ edições"; editar um já aprovado e ver o mesmo badge; rejeitar; vincular evento;
excluir; tentar editar um rejeitado sem `aprovar` e receber 409.

### Implementation for User Story 2

- [ ] T013 [US2] Em `app/api/gastos_read.py`, `api_gastos_list`: quando
  `is_financeiro(current_user)`, usar `gastos_ops.list_expenses_for_admin()` e incluir
  `"totals": gastos_ops.expense_totals(all_expenses)` na resposta (depende de T006, T007, T010).
- [ ] T014 [US2] Em `app/api/gastos_write.py`, novo endpoint `PATCH /api/gastos/<id>`
  (`api_gastos_editar`): RBAC local `gastos_ops.is_financeiro(current_user)` (403 caso
  contrário); parseia o body conforme `contracts/gastos-api.md`; chama `gastos_ops.edit_expense`
  (depende de T008); trata `GastoValidationError`→400 (`fields`), `GastoStateError`→409; retorna
  `_expense_dict(expense)` 200.
- [ ] T015 [US2] Em `app/api/gastos_write.py`: trocar `gastos_ops.is_superadmin(current_user)`
  por `gastos_ops.is_financeiro(current_user)` em `api_gastos_aprovar`, `api_gastos_rejeitar` e
  `api_gastos_vincular_evento` (RBAC só na API — `app/gastos/routes.py` não é tocado).
- [ ] T016 [US2] Em `app/api/gastos_write.py`, `api_gastos_delete`: substituir a chamada a
  `gastos_ops.can_delete_expense` por uma checagem local nova:
  `gastos_ops.is_financeiro(current_user) or (expense.created_by_id == current_user.id and
  expense.status == "pendente")`.
- [ ] T017 [P] [US2] Em `frontend/apps/internal/src/lib/gastos.ts`: novo hook
  `useUpdateGasto()` — `PATCH /api/gastos/:id`, invalida `["gastos-extras"]` (depende de T011).
- [ ] T018 [P] [US2] Criar componente `Modal` local em
  `frontend/apps/internal/src/pages/GastosExtrasPage.tsx` (ou arquivo próprio no mesmo
  diretório): overlay `fixed inset-0 bg-black/50` + painel centralizado, Framer Motion
  (opacity/scale, 150–350ms), `useReducedMotion()`, `Escape`/clique fora fecha.
- [ ] T019 [US2] Em `GastosExtrasPage.tsx`, quando `can_manage`: grid de 4 `KpiCard`
  (Todos/Pendentes/Aprovados/Rejeitados — contagem + `formatBRL` do total, padrão de
  `FinanceiroDashboardPage.tsx`), usando `totals` da API (depende de T013).
- [ ] T020 [US2] Em `GastosExtrasPage.tsx`, tabela densa `w-full` (padrão de
  `PagamentosPage.tsx`) com colunas DATA/DESCRIÇÃO/CATEGORIA/VALOR/STATUS/DESEMBOLSO/EVENTO/
  AUTOR/NOTA FISCAL/AÇÕES, mostrando todas as linhas quando `can_manage`.
- [ ] T021 [US2] Em `GastosExtrasPage.tsx`, ações por linha quando `can_manage`: "Aprovar" (1
  clique, `useApproveGasto` existente, inalterado), "Rejeitar" (existente), "Editar" (abre o
  `Modal` de T018 pré-preenchido, botão "Salvar" chama `useUpdateGasto` sem `aprovar`; se
  `status === "pendente"`, botão extra "Salvar e Aprovar" chama com `aprovar: true`), "Vincular
  evento" (reusa `useGastosEventos`/`useLinkGastoEvento` já existentes), "Ver Nota Fiscal"
  (existente), "Excluir" (`useDeleteGasto` existente, `window.confirm()`).

**Checkpoint**: US1 e US2 funcionam juntas — o financeiro gerencia, o autor vê o resultado
(inclusive o badge "Aprovado c/ edições") na própria visão de US1.

---

## Phase 5: User Story 3 - Cadastro/edição via modal centralizado (Priority: P2)

**Goal**: substituir o formulário fixo do topo por um botão "+ Novo gasto" no cabeçalho que abre
o mesmo `Modal` (de US2) em modo criação, liberando a tela para a tabela.

**Independent Test**: em desktop e mobile, clicar "+ Novo gasto", preencher e cadastrar um
gasto pelo modal (com nota fiscal, radio de 3 opções de desembolso, vínculo de evento opcional),
confirmar que fecha ao concluir/cancelar e que a página nunca rola até um formulário fixo.

### Implementation for User Story 3

- [ ] T022 [US3] Migrar os campos de `NovoGastoForm` (descrição, categoria, `MoneyInput`, data,
  radio "Como será pago?" com as 3 opções — reembolso/fornecedor/sem desembolso definido, bloco
  de evento, `FileUpload` de nota fiscal com limite 10MB, observações) para dentro do `Modal` de
  T018, em modo criação (`useCreateGasto` existente, inalterado).
- [ ] T023 [US3] Em `GastosExtrasPage.tsx`: `PageHeader` com botão "+ Novo gasto" que abre o
  `Modal` em modo criação; remover o formulário fixo do topo da página.
- [ ] T024 [US3] Modo edição do mesmo `Modal` (reusado por T021): mesmos campos exceto
  `FileUpload` (edição não reenvia nota fiscal), pré-preenchido com os dados do gasto.
- [ ] T025 [US3] Conferir o `Modal` em viewport mobile (320–430px): sem rolagem horizontal,
  alvos de toque ≥44px, teclado virtual não esconde o botão de salvar.

**Checkpoint**: as 3 user stories funcionam juntas — fluxo completo ponta a ponta.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T026 `ruff check` nos arquivos Python tocados (`app/models.py`, `app/gastos/gastos_ops.py`,
  `app/api/gastos_read.py`, `app/api/gastos_write.py`, a migration nova).
- [ ] T027 `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [ ] T028 Script de verificação funcional (Flask test client, requests fora de `app_context`)
  contra `manto_local`: cobre criar, editar sem aprovar, "salvar e aprovar" (com e sem mudança
  real de dados), editar um já aprovado, bloqueio de editar rejeitado sem aprovar, RBAC
  (comum/financeiro/superadmin) em todos os endpoints tocados, e que os 7 pontos de
  `status == "aprovado"` no restante do sistema (`app/api/financeiro_read.py`,
  `app/financeiro/routes.py`, `app/calendar/routes.py`, `app/api/agenda_read.py`) continuam
  somando corretamente um gasto "aprovado com edições".
- [ ] T029 Testes Playwright contra o app rodando com `DATABASE_URL=manto_local`: fluxo US1
  (colaborador comum), fluxo US2 (financeiro — KPIs, tabela, editar+aprovar, badge), fluxo US3
  (modal responsivo mobile/desktop).
- [ ] T030 Rodar o roteiro de `quickstart.md` de ponta a ponta, incluindo o passo de confirmar
  que a tela Jinja legada (`app/gastos/routes.py`) continua idêntica.
- [ ] T031 Atualizar `docs/changelog.html` com a entrega, em português simples, republicando no
  link já existente.

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup; BLOQUEIA todas as user stories (schema e núcleo
  de negócio compartilhado).
- **US1 (Phase 3)**: depende só do Foundational — pode ser implementada e testada isoladamente
  (o badge só aparece de fato quando US2 existir para gerar um gasto "aprovado c/ edições", mas
  a leitura/exibição já funciona).
- **US2 (Phase 4)**: depende do Foundational; T013 depende de T010 (US1); é o que efetivamente
  produz o dado que US1 exibe.
- **US3 (Phase 5)**: depende do `Modal` criado em T018 (US2) — reusa o mesmo componente para
  criação e edição.
- **Polish (Phase 6)**: depende de US1+US2+US3 completas.

### Parallel Opportunities

- T005, T006, T007 (funções novas e independentes em `gastos_ops.py`) podem ser feitas em
  paralelo antes de T008.
- T011 (tipos TS) e T017 (hook `useUpdateGasto`) podem ser feitos em paralelo com as tarefas de
  backend correspondentes, já que dependem só do contrato documentado em
  `contracts/gastos-api.md`, não da implementação em si.
- T018 (Modal) é paralelizável em relação a T019/T020 (KPIs/tabela), pois são partes visuais
  independentes da mesma página antes de serem compostas.

## Implementation Strategy

### MVP First

1. Phase 1 (Setup) + Phase 2 (Foundational) — schema e núcleo prontos.
2. Phase 3 (US1) — colaborador comum já registra e acompanha gastos com o novo campo
   `approved_with_edits` disponível (ainda sempre `false` até US2 existir).
3. **Parar e validar**: registrar um gasto como colaborador comum, conferir que só aparece para
   ele.

### Incremental Delivery

1. Foundational → US1 (MVP de leitura) → US2 (gestão completa, onde o "aprovado com edições"
   passa a ser gerado de fato) → US3 (reestruturação visual do cadastro) → Polish.
2. Cada fase termina em um checkpoint testável de ponta a ponta antes de avançar.
