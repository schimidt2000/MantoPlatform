# Implementation Plan: RBAC, edição e "Aprovado com edições" em Gastos Extras

**Branch**: `179-gastos-extras-rbac-edicao` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/179-gastos-extras-rbac-edicao/spec.md`

## Summary

Reestruturar a tela React `/gastos` (Beta) com visão por papel (colaborador comum só vê/gerencia
os próprios gastos; SUPERADMIN e FINANCEIRO ganham visão gerencial completa com 4 KPIs e tabela
global), capacidade de o gestor editar qualquer gasto, e um novo indicador "Aprovado com
edições" para quando a aprovação altera dados do gasto original. Tecnicamente: uma coluna
booleana nova (`approved_with_edits`) em vez de um 4º valor de `status` — para não quebrar os 7
pontos do sistema que já filtram `status == "aprovado"` para cálculos financeiros reais (DRE,
planilha de pagamentos, custo de eventos). Toda a mudança fica isolada no ecossistema React Beta
+ API JSON + núcleo de negócio compartilhado (só com funções novas); a aplicação Jinja legada
não é tocada.

## Technical Context

**Language/Version**: Python 3.14 (Flask) + TypeScript (React 18, Vite)

**Primary Dependencies**: Flask, SQLAlchemy, Flask-Login, Flask-Migrate (Alembic) · React,
TanStack Query, Framer Motion, Tailwind CSS, `@manto/ui`, `@manto/money`, `@manto/api-client`

**Storage**: PostgreSQL (produção via Railway; verificação local sempre contra `manto_local`,
cópia real de produção — nunca SQLite)

**Testing**: Script Python com Flask test client (requests fora de `app_context`) contra
`manto_local`; Playwright para o fluxo end-to-end na tela React

**Target Platform**: Web (SPA servida separadamente do Flask; proxy Vite `/api` → Flask em dev)

**Project Type**: Web application (backend Flask API JSON + frontend React monorepo)

**Performance Goals**: N/A (tela administrativa de baixo volume — dezenas a poucas centenas de
gastos por mês)

**Constraints**: Zero alteração de comportamento na aplicação Jinja legada
(`app/gastos/routes.py`, `app/templates/gastos/*.html`); gastos "aprovado com edições" MUST
continuar contando nos 7 pontos do sistema que somam `status == "aprovado"`
(`app/api/financeiro_read.py`, `app/financeiro/routes.py`, `app/calendar/routes.py`,
`app/api/agenda_read.py`)

**Scale/Scope**: 1 tela React reescrita, 1 coluna nova no banco, 2 módulos de API estendidos, 1
módulo de núcleo de negócio estendido (só adições)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: PASSA. Reusa `NovoGastoForm` atual como base do modal,
  `useGastosEventos`/`useLinkGastoEvento` já existentes, o padrão de tabela de
  `PagamentosPage.tsx` e o padrão de KPI card de `FinanceiroDashboardPage.tsx`. A validação de
  campos do gasto é extraída para uma função só (`_validate_expense_data`), reusada por criar e
  editar — não duplica regra.
- **II. Padrões de código**: PASSA. Novas funções Python com type hints + docstring; novo
  componente `Modal` e hooks TS com interfaces explícitas, zero `any`.
- **III. Arquitetura em camadas**: PASSA. Novo endpoint `PATCH /api/gastos/<id>` só orquestra
  (RBAC + parse + serialização); regra de negócio inteira em `gastos_ops.edit_expense`. Backend
  já é 100% JSON nessa área — nenhum `render_template` introduzido.
- **IV. Não quebrar o que funciona**: PASSA, é o cerne desta decisão de design — a coluna nova
  em vez de um 4º status existe exatamente para não quebrar os 7 pontos de cálculo financeiro
  existentes; e nenhuma função usada pela Jinja legada é alterada (só funções novas na API/ops).
  `tsc`/`ruff`/verificação funcional rodam antes do commit.
- **V. UI/UX com feedback**: PASSA. Todo botão do modal usa `loading` do `Button` existente
  (`@manto/ui`) já usado no formulário atual; erros de validação mantêm os dados preenchidos
  (`ApiRequestError.fields`, padrão já usado em `NovoGastoForm`); exclusão continua via
  `window.confirm()` — padrão já documentado como aceito neste projeto na ausência de um
  `Dialog` compartilhado (não é uma regressão, é o padrão vigente hoje em toda a tela).
- **VI. Planejar antes de codar**: PASSA — spec.md e este plan.md antecedem qualquer código;
  plano técnico já foi validado com o usuário antes da spec.
- **VII. Valores monetários**: PASSA. Reusa `MoneyInput`/`formatBRL` de `@manto/money` sem
  reimplementar máscara; backend recebe/persiste `Decimal`, nunca string formatada.
- **VIII. Mobile-first**: N/A direto (painel interno, não é "superfície pública"), mas o modal
  novo será conferido em viewport mobile antes de "pronto", por ser tela nova tocada.
- **IX. Movimento com propósito**: PASSA. O `Modal` novo usa Framer Motion (opacity/scale,
  150–350ms) respeitando `useReducedMotion()`, no mesmo padrão do drawer de
  `app-layout.tsx:192-205`.

Nenhuma violação — não é necessário preencher Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/179-gastos-extras-rbac-edicao/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/
│   └── gastos-api.md     # Fase 1 — contrato dos endpoints novos/alterados
└── tasks.md               # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── models.py                      # + SpecialExpense.approved_with_edits
├── gastos/
│   ├── gastos_ops.py               # + _validate_expense_data, list_expenses_for_admin,
│   │                                  expense_totals, edit_expense (só adições)
│   └── routes.py                   # INTOCADO (Jinja legado)
├── api/
│   ├── gastos_read.py              # api_gastos_list: RBAC is_financeiro, totals, can_manage
│   └── gastos_write.py             # + PATCH /gastos/<id>; RBAC is_financeiro nos endpoints admin
└── templates/gastos/*.html         # INTOCADO (Jinja legado)

migrations/versions/
└── <nova>_special_expense_approved_with_edits.py

frontend/apps/internal/src/
├── lib/gastos.ts                   # + approved_with_edits, can_manage, totals, useUpdateGasto
├── components/                     # (se promovido) ou local à página: Modal
└── pages/
    └── GastosExtrasPage.tsx        # reescrita: header + KPIs (admin) + tabela densa + modal
```

**Structure Decision**: segue a estrutura já estabelecida pela migração 144/177 — API JSON em
`app/api/`, núcleo de negócio em `app/<blueprint>/<dominio>_ops.py`, tela em
`frontend/apps/internal/src/pages/`, hooks em `frontend/apps/internal/src/lib/`. Nenhum diretório
novo é criado; a única adição estrutural é o componente `Modal` (local à página por ora — ver
`research.md` para a decisão de não promovê-lo a `@manto/ui` neste escopo).

## Complexity Tracking

*Sem violações da constituição — seção não aplicável.*
