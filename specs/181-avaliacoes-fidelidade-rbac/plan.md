# Implementation Plan: Resumo das Avaliações — fidelidade visual e RBAC de anonimato

**Branch**: `181-avaliacoes-fidelidade-rbac` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/181-avaliacoes-fidelidade-rbac/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Reescrever a tela React `/casting/avaliacoes` (`AvaliacaoCastingPage.tsx`) para ter fidelidade
visual e funcional com o painel de avaliações do sistema Jinja legado (`/talents/avaliacoes`,
`app/templates/talents/avaliacoes.html`): filtros em pills (período incl. novo preset "última
semana", modo de data, categoria, evento), KPIs, tendência mensal, distribuição de notas, média
por categoria, ranking de melhores/piores eventos, pontos de atenção e comentários — mantendo a
regra de RBAC já correta no backend (autoria "Anônimo" para todo não-SUPERADMIN; toggle de modo
anônimo total exclusivo do SUPERADMIN). A API (`GET /api/ratings`, `POST /api/ratings/modo-anonimo`)
já retorna todos os dados necessários; a única lacuna é um novo preset de período de 7 dias no
core reusado (`app/talents/rating_ops.py`), aditivo e sem tocar no Jinja legado.

## Technical Context

**Language/Version**: Python 3.11 (backend, Flask) · TypeScript 5 (frontend, React 18 + Vite)

**Primary Dependencies**: Flask + SQLAlchemy (backend); React + TanStack Query + Tailwind CSS +
`@manto/ui` (design system interno) + `@manto/api-client` (frontend) — nenhuma dependência nova.

**Storage**: PostgreSQL (produção via Railway; verificação sempre contra a cópia local
`manto_local`) — nenhuma mudança de schema (`EventRating`/`EventSubRating`/`SiteSetting` já
existentes).

**Testing**: Script Python com o test client do Flask contra `manto_local` (padrão do projeto,
requests fora de `app.app_context()`); `npx tsc --noEmit` e `npm run build` em
`frontend/apps/internal`.

**Target Platform**: Web — staff autenticado (desktop widescreen como caso principal desta
feature; mobile deve continuar funcional sem regressão).

**Project Type**: Web application (SPA React desacoplada consumindo API Flask JSON) — monorepo
`frontend/` (workspace `apps/internal`) + backend Flask `app/`.

**Performance Goals**: Sem meta nova de performance — mesma resposta já usada hoje por
`GET /api/ratings` (uma consulta agregada por carregamento de filtro).

**Constraints**: Não alterar nenhuma rota/view/template do Jinja legado
(`app/talents/routes.py`, `app/templates/talents/avaliacoes.html`); não introduzir biblioteca de
gráficos nova (gráficos em barra simples com Tailwind, como já feito em `DonutChart`/`SectorPanel`
da feature 174); não alterar o contrato RBAC já correto no backend, só consumi-lo fielmente no
frontend.

**Scale/Scope**: 1 tela React reescrita por completo + 1 pequeno acréscimo aditivo no backend
(novo preset de período). Sem novas tabelas, sem novos endpoints.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar** — PASS. Reusa `useRatingsOverview`/`useToggleAnonymousMode`
  (`lib/ratings.ts`), `rating_ops.build_overview`/`serialize_overview`, e os componentes de design
  system já existentes (`Card`, `DenseCard`, `Button`, `Input`, `PageHeader`, `Skeleton`,
  `MetricBadge`). Nenhum componente novo de "pill" — reusa o padrão `Button
  variant=default/outline` já usado em `FinanceiroDashboardPage.tsx`/`AdminDesempenhoPage.tsx`.
- **II. Padrões de código** — PASS. TS estrito (sem `any`), Python com type hints/docstrings já
  presentes em `rating_ops.py` (será só estendido).
- **III. Arquitetura desacoplada (API First)** — PASS. Nenhuma rota nova; `app/api/ratings_read.py`
  continua só validando RBAC e serializando; `rating_ops.py` continua puro (sem `flask.request`).
- **IV. Não quebrar o que funciona** — PASS (gate ativo nesta feature). A view Jinja legada
  (`app/talents/routes.py::avaliacoes()`) e seu template continuam usando os presets existentes
  (`30d`/`90d`/`365d`/`custom`/`all`) sem qualquer alteração de comportamento; o novo preset `7d`
  é aditivo em `_PERIOD_PRESETS`/`PERIOD_LABELS` e só é exercitado pela nova UI React. `tsc`/build
  e o script de verificação contra `manto_local` cobrem a não-regressão antes do commit.
- **V. UI/UX consistente com feedback** — PASS. Loading via `Skeleton`, erro via alerta
  `bg-red-soft`/`text-red` (mesmo padrão das outras páginas), toggle de modo anônimo com estado
  de `loading`/disabled no `Button` (Princípio V, botão nunca "morto" ao clique).
- **VI. Planejar antes de codar** — PASS (este próprio pipeline specify→plan→tasks→implement).
- **VII. Valores monetários em padrão BR** — N/A (tela não exibe valores monetários).
- **VIII. Superfícies públicas mobile-first** — N/A (superfície interna/staff, não pública), mas
  a tela permanece utilizável em mobile por não-regressão (FR-020).
- **IX. Movimento com propósito (Framer Motion)** — PASS parcial: transições de troca de filtro/
  categoria usam as mesmas classes utilitárias Tailwind (`transition-colors`) já usadas nos pills
  de `Button`; não há modais/drawers nesta tela que exijam Framer Motion dedicado.

Nenhuma violação — não é necessário preencher a seção de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/181-avaliacoes-fidelidade-rbac/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ratings-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
Manto_Platform/
├── app/
│   └── talents/
│       └── rating_ops.py         # ALTERADO (aditivo): novo preset "7d" em _PERIOD_PRESETS/PERIOD_LABELS
│   # app/api/ratings_read.py, app/api/ratings_write.py — SEM mudança (contrato já suficiente)
│   # app/talents/routes.py, app/templates/talents/avaliacoes.html — INTOCADOS (Jinja legado)
│
└── frontend/apps/internal/src/
    ├── lib/
    │   └── ratings.ts            # ALTERADO: tipo de period aceita "7d"
    └── pages/
        └── AvaliacaoCastingPage.tsx   # REESCRITO por completo (pills, KPIs, gráficos, layout widescreen)
```

**Structure Decision**: Web application já existente (monorepo `frontend/` + backend Flask `app/`).
Esta feature é quase inteiramente frontend (`frontend/apps/internal`), com uma única alteração
aditiva de backend (`app/talents/rating_ops.py`) reusada por API e Jinja sem quebrar nenhum dos
dois consumidores.

## Complexity Tracking

*Não aplicável — nenhuma violação de constituição identificada.*
