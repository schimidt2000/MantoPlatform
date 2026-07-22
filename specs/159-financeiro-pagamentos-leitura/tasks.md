# Tasks: Planilha de Pagamentos em React (Leitura) (159)

**Input**: Design documents from `specs/159-financeiro-pagamentos-leitura/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/financeiro-pagamentos-endpoint.md,
quickstart.md

**Tests**: verificação é o script de paridade `scripts/db/verify_159_financeiro_pagamentos.py`
contra `manto_local`, gerado na Phase de Polish.

**Organização**: story única (US1, P1) — não há uma segunda user story nesta fatia.

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` (Postgres) atualizado (`python -m flask db heads`) — sem
      migration nova nesta fatia.

## Phase 2: Foundational

Nenhuma — núcleo (`_pagamentos_query`, `_ensure_salary_payments`, `_build_payment_items`,
`_build_bv_items`, `_build_commission_items`, `_build_recurring_items`,
`_resync_pending_commissions`) já existe em `app/financeiro/routes.py`.

## Phase 3: User Story 1 — Ver a planilha de pagamentos do mês em React (P1)

**Goal**: usuário Financeiro/Superadmin vê todos os itens de pagamento do mês (cachês, salários,
BV, comissões, recorrentes) e os 5 totais inteiramente pela tela React, com paridade exata com a
tela antiga.

**Independent Test**: abrir a tela de pagamentos em React para um mês qualquer, com um usuário
Financeiro, e conferir paridade de itens e totais com a tela antiga (`/financeiro/pagamentos`)
para o mesmo mês.

- [X] T002 [US1] Implementar `GET /api/financeiro/pagamentos` em `app/api/financeiro_read.py`
      (adiciona ao arquivo já existente, ao lado de `api_vendas_pipeline`/
      `api_financeiro_dashboard`/`api_financeiro_comissoes`): gate `_has_role(FINANCEIRO,
      SUPERADMIN)`; resolve mês via mesmo fallback de `pagamentos()`; chama
      `_resync_pending_commissions()` e `_ensure_salary_payments(year, month)`; monta a mesma
      combinação de itens (`_pagamentos_query`+`_build_payment_items` com `SalaryPayment`s e
      `SpecialExpense`s do mês, `_build_bv_items`, `_build_commission_items` do ciclo do mês
      anterior, `_build_recurring_items` após `ensure_recurring_entries`); calcula os 5 totais
      (`total`, `pago`, `no_banco`, `pendente`, `futuro`) igual a `pagamentos()`.
- [X] T003 [P] [US1] Implementar `_serialize_pagamento_item(item)` em
      `app/api/financeiro_read.py`: campos comuns (tipo, data ISO, favorecido, evento, `amount`
      float, PIX, status, `is_future`) + específicos por tipo (`gross_amount`/`advance_amount`/
      `advances` para `salary` — `advances` re-lida de `SalaryAdvance.query.filter_by
      (salary_payment_id=item["id"])`, não da string BRL pré-formatada; `missing_data` para `bv`).
      Serializa conforme `contracts/financeiro-pagamentos-endpoint.md`.
- [X] T004 [P] [US1] Criar `usePagamentos(month)` em `frontend/apps/internal/src/lib/financeiro.ts`
      (arquivo já existe, da 157/158) — `useQuery` contra `/api/financeiro/pagamentos` com `month`
      na query string.
- [X] T005 [US1] Criar `frontend/apps/internal/src/pages/PagamentosPage.tsx` (NOVO): seletor de
      mês (`YYYY-MM`), os 5 totais do mês em destaque, lista única de itens (badge de tipo, data,
      favorecido, evento, valor, PIX, badge de status, indicador de futuro/dados pendentes);
      drill-down de adiantamentos para itens de salário. Sem ação de escrita nesta fatia. Valores
      formatados com `formatBRL` (`@manto/money`); loading (skeleton) e estado vazio amigável;
      mobile-first (lista com scroll horizontal no card, mesmo padrão da 156/157/158).
- [X] T006 [US1] Adicionar rota `/financeiro/pagamentos` em `App.tsx` (+ item de navegação, mesmo
      padrão das rotas anteriores).

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 4: Polish & Verificação

- [X] T007 Criar `scripts/db/verify_159_financeiro_pagamentos.py` (gitignored): test client Flask
      contra `manto_local`, requests fora de `app_context` — cobre paridade de itens (por tipo,
      valores, status, `is_future`, `missing_data`, adiantamentos) e dos 5 totais entre API e
      `pagamentos()`, para um mês com cada tipo de item presente (cachê, salário com adiantamento,
      BV sem PIX, comissão, recorrente), filtro de mês (válido/inválido/default), e o gate 403
      para papel fora de Financeiro/Superadmin.
- [X] T008 Rodar `ruff check app/` nos arquivos tocados.
- [X] T009 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [ ] T010 Conferência mobile (320–430px) da tela de pagamentos (lista com scroll horizontal,
      Princípio VIII) — **não verificado nesta sessão**: sem Playwright/chromium-cli disponível
      no ambiente (mesma limitação da 157/158). Classes mobile-first (`overflow-x-auto` no card
      de itens) seguem o mesmo padrão já usado e conferido na 156/157/158; recomenda-se
      conferência visual manual antes do merge, se possível.
- [X] T011 Atualizar `docs/changelog.html` com entrada em linguagem simples (entrada 159) e
      republicar no artifact já existente (mesmo link).

## Dependencies

Setup (Phase 1) → Foundational (Phase 2, vazia) → US1 (Phase 3) → Polish (Phase 4).
Dentro da story: endpoint API + serializer → hook frontend → página → rota.

## Implementation Strategy

MVP = a própria US1 (story única desta fatia). Com esta fatia, a US4 fica completa em leitura;
escrita (marcar status, ações em massa, adiantamento, exportação) fica para uma fatia futura.
