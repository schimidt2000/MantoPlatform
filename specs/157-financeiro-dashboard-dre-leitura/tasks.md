# Tasks: Dashboard Financeiro (DRE) em React (Leitura) (157)

**Input**: Design documents from `specs/157-financeiro-dashboard-dre-leitura/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/financeiro-dashboard-endpoint.md,
quickstart.md

**Tests**: verificação é o script de paridade `scripts/db/verify_157_financeiro_dashboard.py`
contra `manto_local`, gerado na Phase de Polish.

**Organização**: story única (US1, P1) — não há uma segunda user story nesta fatia.

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` (Postgres) atualizado (`python -m flask db heads`) — sem
      migration nova nesta fatia.

## Phase 2: Foundational

Nenhuma — núcleo (`_resolve_period`/`_compute_drg`/`_salary_cost`/`_group_cost`/`_event_cost`/
`_event_commission`/`_get_commission_rate`/`_is_permuta`/`_pct`/`_get_fator_r_threshold`/
`_get_tax_rate`/`_month_range`/`_prev_month`/`_month_refs_between`) já existe em
`app/financeiro/routes.py`.

## Phase 3: User Story 1 — Ver o dashboard financeiro (DRE) em React (P1)

**Goal**: usuário Financeiro/Superadmin vê o painel gerencial completo do período (DRE, KPIs,
painéis, tabela de eventos, pendências) inteiramente pela tela React.

**Independent Test**: abrir o dashboard em React para um período qualquer e conferir paridade
de valores com a tela antiga (`/financeiro/`) para o mesmo usuário e mesmo período.

- [X] T002 [US1] Implementar `GET /api/financeiro/dashboard` em `app/api/financeiro_read.py`
      (adiciona ao arquivo já existente, ao lado de `api_vendas_pipeline`): gate paridade com
      `require_financeiro`; resolve período via `_resolve_period`; monta a mesma query de
      eventos de `dashboard()` (`app/financeiro/routes.py:387`); serializa `dre`
      (realizado/projetado/total via `_compute_drg`), `kpis`, `paineis`, `eventos`, `pendencias`
      conforme `contracts/financeiro-dashboard-endpoint.md`.
- [X] T003 [P] [US1] Criar `useFinanceiroDashboard(period, start?, end?)` em
      `frontend/apps/internal/src/lib/financeiro.ts` (NOVO) — `useQuery` contra
      `/api/financeiro/dashboard` com os params de período na query string.
- [X] T004 [US1] Criar `frontend/apps/internal/src/pages/FinanceiroDashboardPage.tsx` (NOVO):
      seletor de período (este mês/30d/mês anterior/custom com inputs de data), seção DRE (3
      colunas), tira de KPIs (ticket médio, ratio custo-talento, break-even, Fator R), painéis
      laterais (receita por tipo, top vendedores, tendência mensal, auditoria), tabela de
      eventos do período (status financeiro por linha, link "Ver" para `/events/:id`), painel de
      pendências (recebimentos previstos, notas fiscais). Valores formatados com `formatBRL`
      (`@manto/money`); loading (skeleton) e estado vazio amigável; mobile-first (painéis em
      coluna única <768px, tabela com scroll horizontal no card).
- [X] T005 [US1] Adicionar rota `/financeiro` em `App.tsx` (+ item de navegação, mesmo padrão
      das rotas anteriores).

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 4: Polish & Verificação

- [X] T006 Criar `scripts/db/verify_157_financeiro_dashboard.py` (gitignored): test client Flask
      contra `manto_local`, requests fora de `app_context` — cobre paridade de valores (DRE
      realizado/projetado/total, KPIs, tabela de eventos, pendências) entre API e
      `dashboard()`/`pipeline()`, para os 4 filtros de período, exclusão de satélite, e o gate
      403 para papel fora de Financeiro/Superadmin.
- [X] T007 Rodar `ruff check app/` nos arquivos tocados.
- [X] T008 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [ ] T009 Conferência mobile (320–430px) do dashboard (painéis empilhados, tabela com scroll
      horizontal, Princípio VIII) — **não verificado nesta sessão**: sem ferramenta de
      browser/screenshot disponível no ambiente. Classes mobile-first (`sm:grid-cols-*`,
      `overflow-x-auto` nos cards de tabela) seguem o mesmo padrão já usado e conferido na 156;
      recomenda-se conferência visual manual antes do merge, se possível.
- [X] T010 Atualizar `docs/changelog.html` com entrada em linguagem simples, republicando no
      mesmo link existente.

## Dependencies

Setup (Phase 1) → Foundational (Phase 2, vazia) → US1 (Phase 3) → Polish (Phase 4).
Dentro da story: endpoint API → hook frontend → página → rota.

## Implementation Strategy

MVP = a própria US1 (story única desta fatia). Fatias futuras da US4 (planilha de pagamentos,
funcionário/salário, comissões) seguem cada uma com seu próprio ciclo completo.
