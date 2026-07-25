---

description: "Task list for feature 187 — Reestruturação do Módulo de Comissões"
---

# Tasks: Reestruturação do Módulo de Comissões

**Input**: Design documents from `specs/187-comissoes-modulo-completo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/comissoes-api.md, quickstart.md

**Tests**: Sem TDD por-story (não solicitado). O portão de qualidade obrigatório do projeto —
script de verificação funcional contra `manto_local` cobrindo os 3 papéis e a atomicidade — é
a Tarefa T024, na fase de Polish, pois só pode validar o fluxo completo depois que leitura e
escrita existirem.

**Organization**: Tarefas agrupadas por user story (US1/US2/US3, prioridades da spec.md).

## Path Conventions

Web app já existente: backend `app/`, frontend `frontend/apps/internal` + `frontend/packages/ui`
(ver "Project Structure" em `plan.md`).

---

## Phase 1: Setup

**Purpose**: Nenhuma inicialização de projeto nova é necessária (stack e diretórios já existem).
Único passo de setup é confirmar o ambiente de verificação.

- [X] T001 Confirmar `manto_local` (Postgres) atualizada e app rodando via `.\scripts\db\run-local.ps1` (ver `quickstart.md`) antes de iniciar qualquer implementação

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: núcleo de negócio puro e componentes de UI compartilhados dos quais as 3 user
stories dependem.

**⚠️ CRITICAL**: nenhuma user story pode começar antes desta fase.

- [X] T002 Criar `app/financeiro/comissoes_ops.py` com `month_bounds(year, month)`, tipos `CommissionKpis`/`CommissionMonthSummaryRow`/`CommissionEntry`/`PayoutResult` (dataclasses, ver `data-model.md`) — sem lógica ainda, só as assinaturas e docstrings
- [X] T003 [P] Em `app/financeiro/comissoes_ops.py`, implementar `get_month_kpis(month, seller_id=None) -> CommissionKpis` — soma `total_month`/`total_paid`/`total_pending` via query agregada (`db.func.sum`), reusando o mesmo filtro de mês de `api_financeiro_comissoes` (`sale_date` no mês OU `sale_date IS NULL` com `created_at` no mês)
- [X] T004 [P] Em `app/financeiro/comissoes_ops.py`, implementar `get_month_summary_by_seller(month, seller_id=None) -> list[CommissionMonthSummaryRow]` — agrupa por vendedor, calcula `sale_count`, `total_amount`, `pending_amount`, `month_status` e a lista de `entries` (accordion)
- [X] T005 [P] Em `app/financeiro/comissoes_ops.py`, implementar `get_month_entries(month, seller_id=None, event_name=None, status=None) -> list[CommissionEntry]` — visão analítica com os mesmos filtros de texto/status pedidos por FR-008
- [X] T006 Em `app/financeiro/comissoes_ops.py`, implementar `pay_seller_month(seller_id, month, actor_id) -> PayoutResult` — usa `with_for_update()` nos registros `a_pagar` elegíveis do vendedor/mês, seta `status='pago'`/`paid_at=date.today()` (fuso `America/Sao_Paulo`), `db.session.commit()` único, `db.session.rollback()` em qualquer exceção antes do commit (ver `research.md` §4); NÃO chama `_bulk_set_commission_period` nem duplica sua lógica
- [X] T007 [P] Criar `frontend/packages/ui/src/components/dialog.tsx` — `Dialog`/`DialogContent`/`DialogHeader`/`DialogTitle`/`DialogFooter` (portal, foco preso, `Escape`/clique-fora fecham, animação Framer Motion respeitando `useReducedMotion()`), sem dependência nova de pacote
- [X] T008 [P] Criar `frontend/packages/ui/src/components/tabs.tsx` — `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent` controlado (state simples, transição de conteúdo via Framer Motion)
- [X] T009 [P] Criar `frontend/packages/ui/src/components/accordion-row.tsx` — linha expansível simples (altura animada via Framer Motion, respeitando `useReducedMotion()`)
- [X] T010 Exportar `Dialog`+subcomponentes, `Tabs`+subcomponentes e `AccordionRow` em `frontend/packages/ui/src/index.ts`

**Checkpoint**: com T002–T010 prontos, as 3 user stories podem ser implementadas.

---

## Phase 3: User Story 1 - Vendedor acompanha suas próprias comissões (Priority: P1) 🎯 MVP

**Goal**: vendedor comum abre "Minhas Comissões" e só vê/consegue ler os próprios dados; nenhuma
ação de pagamento acessível nem no cliente nem no servidor.

**Independent Test**: logar como usuário só-Comercial, abrir a tela, confirmar título "Minhas
Comissões", nenhum outro `seller_id` nos dados retornados, nenhum botão de pagamento, e uma
chamada direta ao endpoint de liquidação retornando 403.

### Implementation for User Story 1

- [X] T011 [US1] Reescrever `GET /api/financeiro/comissoes` em `app/api/financeiro_read.py` para usar `comissoes_ops.get_month_kpis`/`get_month_summary_by_seller`/`get_month_entries`, retornando o payload do contrato (`title`, `kpis`, `by_seller`, `entries`, `can_manage`); quando `can_manage=False`, forçar `seller_id=current_user.id` em todas as três chamadas (nunca aceitar `seller_id` da query string nesse caso)
- [X] T012 [US1] Em `app/api/financeiro_write.py`, criar a rota `POST /financeiro/comissoes/pagar-mes` chamando `_require_financeiro()` primeiro (403 imediato para papel Comercial, cobrindo FR-003/SC-005) e só então `comissoes_ops.pay_seller_month`
- [X] T013 [US1] Em `frontend/apps/internal/src/lib/financeiro.ts`, atualizar o tipo `CommissionEntry`/adicionar `CommissionKpis`, `CommissionMonthSummaryRow`, `ComissoesPayload` e evoluir `useComissoes(month, sellerId?)` para o novo payload
- [X] T014 [US1] Reescrever `frontend/apps/internal/src/pages/ComissoesPage.tsx`: título condicional (`payload.title`), 3 cards de KPI (`Total de Comissões do Mês`, `Total Pago` verde, `A Pagar/Pendente` amarelo/roxo) usando `MetricBadge`/`Card` de `@manto/ui`, e ocultar toda ação de pagamento quando `can_manage=false`

**Checkpoint**: US1 funcional e testável de forma independente (vendedor comum só lê os
próprios dados; RBAC de escrita já rejeita no servidor mesmo sem UI para a ação).

---

## Phase 4: User Story 2 - Financeiro/Superadmin fecha o pagamento do mês por vendedor (Priority: P1)

**Goal**: Financeiro/Superadmin liquida o mês de um vendedor em uma ação atômica, com modal de
confirmação mostrando o valor exato, e a UI reflete o novo estado sem F5.

**Independent Test**: logar como Financeiro, mês com pendências, clicar "Pagar Mês" → modal com
valor certo → confirmar → todos os registros elegíveis viram `pago`, KPIs/status atualizam sem
reload; repetir a chamada e confirmar `changed_count: 0` sem erro (idempotência, edge case da spec).

### Implementation for User Story 2

- [X] T015 [US2] Em `frontend/apps/internal/src/lib/financeiro.ts`, adicionar `usePagarMesComissao()` (mutation TanStack Query para `POST /financeiro/comissoes/pagar-mes`) que invalida a query de `useComissoes` no `onSuccess` (FR-013 — atualização sem F5)
- [X] T016 [US2] Em `ComissoesPage.tsx`, adicionar o seletor de Mês/Ano (`YYYY-MM`) e o filtro rápido por vendedor, visíveis somente quando `can_manage=true` (FR-004)
- [X] T017 [US2] Em `ComissoesPage.tsx`, criar a aba "Resumo por Vendedor" (usando `Tabs` de T008): tabela agrupada (Vendedor | Qtd de Vendas | Valor Total | Status do Mês | Ações), botão primário "Pagar Mês (R$ X.XXX,XX)" habilitado só quando `month_status='pendente'` e `pending_amount > 0`
- [X] T018 [US2] Em `ComissoesPage.tsx`, usar `AccordionRow` (T009) para expandir cada linha de vendedor e listar os `entries` que compõem o total (FR-007)
- [X] T019 [US2] Criar o modal de confirmação de pagamento usando `Dialog` (T007): "Confirmar pagamento de R$ X.XXX,XX para [Nome do Vendedor] relativo ao mês [YYYY-MM]?", com botão de confirmação em estado de loading durante a mutation (Princípio V — nenhum botão morto ao clique) e toast de sucesso/erro em pt-BR
- [X] T020 [US2] Registrar auditoria da liquidação em `comissoes_ops.pay_seller_month` via `app.utils.audit` (ator, vendedor, mês, valor total, quantidade de registros — FR-016)

**Checkpoint**: US1 + US2 funcionam juntas — vendedor comum só lê; Financeiro liquida com
segurança e feedback imediato.

---

## Phase 5: User Story 3 - Financeiro/Superadmin analisa e exporta o detalhamento do mês (Priority: P2)

**Goal**: aba "Detalhamento de Vendas" com filtros por evento/status, e exportação CSV do resumo
do mês.

**Independent Test**: com um mês com comissões pagas e pendentes de vários vendedores, alternar
para "Detalhamento de Vendas", filtrar por status "A pagar", depois exportar o CSV e conferir que
os totais batem com os KPIs da tela.

### Implementation for User Story 3

- [X] T021 [US3] Em `ComissoesPage.tsx`, criar a aba "Detalhamento de Vendas" (tabela: Data da Venda | Vendedor | Evento | Valor | Status | Pago em | Ações) consumindo `payload.entries`
- [X] T022 [US3] Em `ComissoesPage.tsx`, adicionar filtro textual por nome de evento e filtro por status (`A pagar`/`Pago`) na aba de detalhamento — filtragem no cliente sobre `payload.entries` já carregado (mesmo mês/vendedor da query ativa)
- [X] T023 [US3] Em `frontend/apps/internal/src/lib/financeiro.ts` (ou um novo `lib/csv.ts` se a lógica crescer), implementar `exportComissoesCsv(bySeller: CommissionMonthSummaryRow[], month: string)` — gera e baixa um CSV client-side (vendedor, quantidade de vendas, valor total, status), acionado pelo botão "Exportar Relatório (CSV)" visível só quando `can_manage=true`

**Checkpoint**: todas as 3 user stories funcionam de forma independente e integrada.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T024 Criar `scripts/db/verify_187_comissoes.py` (test client do Flask contra `manto_local`, requests fora de `app_context`) cobrindo os 5 cenários listados em `quickstart.md` (leitura restrita do vendedor comum, 403 na liquidação para papel Comercial, liquidação bem-sucedida do Financeiro, idempotência da segunda chamada, KPIs batendo com `SUM()` direto) e executá-lo
- [X] T025 [P] `ruff check app/financeiro/comissoes_ops.py app/api/financeiro_read.py app/api/financeiro_write.py` sem warnings
- [X] T026 [P] `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal` sem erros
- [X] T027 Conferir a tela no navegador (papéis Comercial e Financeiro), viewport estreito incluso, confirmando transições Framer Motion (modal, abas, accordion) e feedback de loading em todo botão de ação (Portão de Qualidade da constituição)
- [X] T028 Atualizar `docs/changelog.html` com uma entrada em português simples descrevendo a reestruturação da tela de Comissões, republicando no link já existente

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as user stories
- **US1 (Phase 3)**: depende só do Foundational
- **US2 (Phase 4)**: depende do Foundational; T015–T020 assumem que T011 (payload) e T013
  (tipos no `financeiro.ts`) de US1 já existem, já que reaproveitam o mesmo hook de leitura
- **US3 (Phase 5)**: depende do Foundational e do payload de US1 (T011/T013); independente de US2
- **Polish (Phase 6)**: depende de US1+US2+US3 completas

### Parallel Opportunities

- T003, T004, T005 (funções de leitura em `comissoes_ops.py`) são paralelas entre si (T002 as
  precede, define os tipos primeiro)
- T007, T008, T009 (componentes novos de `@manto/ui`) são paralelos entre si
- T025 e T026 (lint e typecheck) são paralelos entre si, ambos depois de toda a implementação

---

## Implementation Strategy

### MVP First

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1)
2. **PARAR E VALIDAR**: vendedor comum só lê os próprios dados, RBAC de escrita já rejeita no
   servidor mesmo sem a UI de pagamento existir ainda — MVP seguro para expor mesmo antes de US2.

### Incremental Delivery

1. Foundational pronto → US1 (leitura + RBAC) → US2 (liquidação em lote, a correção do bug
   original) → US3 (detalhamento + export) → Polish (verificação funcional obrigatória + changelog)
