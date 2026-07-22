# Tasks: Comissões em React (Leitura) (158)

**Input**: Design documents from `specs/158-comissoes-leitura/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/financeiro-comissoes-endpoint.md,
quickstart.md

**Tests**: verificação é o script de paridade `scripts/db/verify_158_financeiro_comissoes.py`
contra `manto_local`, gerado na Phase de Polish.

**Organização**: story única (US1, P1) — não há uma segunda user story nesta fatia.

## Phase 1: Setup

- [ ] T001 Confirmar `manto_local` (Postgres) atualizado (`python -m flask db heads`) — sem
      migration nova nesta fatia.

## Phase 2: Foundational

Nenhuma — núcleo (`comissoes()`, `_resync_pending_commissions`, `_COMMISSION_STATUS_LABELS`,
`_can_view_vendas`) já existe em `app/financeiro/routes.py` e `app/api/financeiro_read.py`.

## Phase 3: User Story 1 — Ver as comissões do mês em React (P1)

**Goal**: usuário Financeiro/Superadmin, Comercial ou responsável EducaManto vê a lista de
comissões do mês (entries + estornos pendentes) e o total a pagar inteiramente pela tela React,
com o recorte correto (completo ou só as próprias).

**Independent Test**: abrir a tela de comissões em React para um mês qualquer, com um usuário
Financeiro e com um usuário Comercial, e conferir paridade de valores com a tela antiga
(`/financeiro/comissoes`) para o mesmo usuário e mesmo mês.

- [ ] T002 [US1] Implementar `GET /api/financeiro/comissoes` em `app/api/financeiro_read.py`
      (adiciona ao arquivo já existente, ao lado de `api_vendas_pipeline`/
      `api_financeiro_dashboard`): gate paridade com `require_vendas` (reusa `_can_view_vendas`);
      resolve mês via mesmo fallback de `comissoes()`; chama `_resync_pending_commissions()`;
      monta a mesma query de `CommissionPayment` (entries do mês + estornos pendentes),
      restringindo a `seller_id=current_user.id` quando `can_manage=False`; serializa conforme
      `contracts/financeiro-comissoes-endpoint.md` (`entries`, `estornos`, `total_a_pagar`,
      `can_manage`, `sellers` quando `can_manage`).
- [ ] T003 [P] [US1] Criar `useComissoes(month)` em `frontend/apps/internal/src/lib/financeiro.ts`
      (arquivo já existe, da 157) — `useQuery` contra `/api/financeiro/comissoes` com `month` na
      query string.
- [ ] T004 [US1] Criar `frontend/apps/internal/src/pages/ComissoesPage.tsx` (NOVO): seletor de mês
      (`YYYY-MM`), total a pagar do mês, tabela de comissões (vendedor, evento, data da venda,
      valor, status, data de pagamento), tabela de estornos pendentes (quando houver). Sem ação
      de escrita nesta fatia. Valores formatados com `formatBRL` (`@manto/money`); loading
      (skeleton) e estado vazio amigável; mobile-first (tabelas com scroll horizontal no card,
      mesmo padrão da 156/157).
- [ ] T005 [US1] Adicionar rota `/financeiro/comissoes` em `App.tsx` (+ item de navegação, mesmo
      padrão das rotas anteriores).

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 4: Polish & Verificação

- [ ] T006 Criar `scripts/db/verify_158_financeiro_comissoes.py` (gitignored): test client Flask
      contra `manto_local`, requests fora de `app_context` — cobre paridade de valores (entries,
      estornos, total a pagar) entre API e `comissoes()`, para um usuário Financeiro e para um
      usuário Comercial (visão restrita), filtro de mês (válido/inválido/default), e o gate 403
      para papel fora de Comercial/Financeiro/Superadmin/responsável EducaManto.
- [ ] T007 Rodar `ruff check app/` nos arquivos tocados.
- [ ] T008 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [ ] T009 Conferência mobile (320–430px) da tela de comissões (tabelas com scroll horizontal,
      Princípio VIII) — sujeita à disponibilidade de ferramenta de browser/screenshot no
      ambiente; se indisponível, registrar como pendência explícita (mesmo caso da 157).
- [ ] T010 Atualizar `docs/changelog.html` com entrada em linguagem simples, republicando no
      mesmo link existente.

## Dependencies

Setup (Phase 1) → Foundational (Phase 2, vazia) → US1 (Phase 3) → Polish (Phase 4).
Dentro da story: endpoint API → hook frontend → página → rota.

## Implementation Strategy

MVP = a própria US1 (story única desta fatia). Fatia futura da US4 (planilha de pagamentos)
segue com seu próprio ciclo completo.
