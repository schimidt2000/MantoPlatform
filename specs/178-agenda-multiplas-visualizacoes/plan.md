# Implementation Plan: Agenda com múltiplas visualizações (Mês, Dia, Lista)

**Branch**: `178-agenda-multiplas-visualizacoes` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/178-agenda-multiplas-visualizacoes/spec.md`

## Summary

Refinar a tela `/agenda` (React, `frontend/apps/internal`) para oferecer 3 visualizações
alternáveis — Mês (grade já existente), Dia (nova: linha do tempo 00:00–23:00 com sobreposição
lado a lado) e Lista (nova: feed agrupado por dia) — com uma barra de ferramentas comum
(seletor de visão + navegação ‹/Hoje/›) e layout de largura total. É uma feature 100%
frontend: os dois endpoints necessários (`GET /api/agenda?ym=`, `GET /api/agenda/day/<data>`)
já existem e já retornam todos os campos exigidos (horário, categoria derivada do título,
local); o endpoint de dia já existe no backend mas hoje não tem nenhum consumidor no React.

## Technical Context

**Language/Version**: TypeScript 5.x (strict) — React 18, Vite

**Primary Dependencies**: React Router (navegação `/agenda`), TanStack Query (`useAgenda`/`useAgendaDia` já existentes em `lib/agenda.ts`), Framer Motion (transições entre visões, Princípio IX), Tailwind CSS + `@manto/ui` (Button, PageHeader, Skeleton)

**Storage**: N/A — nenhuma mudança de banco; feature consome dados já persistidos via API existente

**Testing**: Verificação funcional manual do fluxo React (não há suíte automatizada de frontend no projeto); `npx tsc --noEmit` + `npm run build` como portão de tipo/build; verificação visual via Playwright (desktop widescreen + mobile) antes do merge, por instrução explícita do usuário

**Target Platform**: Web — navegador desktop (widescreen ≥1920px) e mobile (320–430px), staff autenticado (`frontend/apps/internal`)

**Project Type**: Web application (frontend React consumindo API Flask já existente) — só o lado frontend é tocado nesta feature

**Performance Goals**: Troca de visão/navegação de período deve ser percebida como instantânea (sem novo fetch quando os dados do período já estão em cache do TanStack Query); nenhuma meta numérica adicional além do padrão já usado no restante da SPA

**Constraints**: Não introduzir nenhum novo endpoint de API nem alterar o formato de resposta dos dois endpoints existentes (`build_agenda_month`, `api_agenda_day`) — a spec assume reuso total dos campos já serializados em `EventoResumo`

**Scale/Scope**: 1 página existente refatorada (`AgendaPage.tsx`) + 2 novas visões (Dia, Lista) + pequenos ajustes no componente de grade mensal já existente (`CalendarGrid.tsx`) para clique-no-dia; sem novas rotas de página (tudo dentro de `/agenda`, estado de visão fica na URL via query string para permitir compartilhar/voltar)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Princípio I (Reutilizar antes de criar)**: PASSA. Reaproveita `useAgenda`/`useAgendaDia` (já existentes, o segundo sem consumidor até agora), `eventCategory.ts` (paleta única), `CalendarGrid.tsx` (estendido, não duplicado), `PageHeader`/`Button`/`Skeleton` de `@manto/ui`. Nenhuma lógica de negócio nova no backend — os dois `*_ops`/serializers de agenda já cobrem o necessário.
- **Princípio II (TS estrito)**: PASSA (a garantir na implementação) — todo componente novo (`DayTimelineView`, `AgendaListView`, `AgendaToolbar`) com props tipadas, sem `any`.
- **Princípio III (API First / camadas)**: PASSA. Nenhuma rota nova; se o endpoint de dia precisar de ajuste pontual, ele continua uma função pura chamada pela view, sem lógica de negócio no componente React além de cálculo de layout (posicionamento vertical/colunas), que é puramente de apresentação.
- **Princípio IV (Não quebrar o que funciona)**: PASSA — `tsc --noEmit` e `npm run build` rodam antes do commit; a visão Mês mantém o comportamento de clique-no-evento intocado (FR-007); verificação visual real antes de declarar pronto.
- **Princípio V (UI/UX com feedback)**: PASSA — visões novas reusam os mesmos estados de loading/erro/vazio já usados na visão Mês (`Skeleton`, mensagem de erro pt-BR, estado vazio).
- **Princípio VII (Dinheiro em BRL)**: N/A — a agenda não exibe valores monetários (confirmado: `EventoResumo` não tem campo financeiro).
- **Princípio VIII (Mobile-first em superfícies públicas)**: N/A formalmente (Agenda é área interna/staff, não superfície pública), mas a spec (FR-017, SC-004) exige adaptação mobile mesmo assim — tratada com o mesmo rigor.
- **Princípio IX (Movimento com propósito)**: PASSA — troca de visão e navegação ‹/›/Hoje usam transição Framer Motion (150–350ms, `easeOut`), respeitando `useReducedMotion()` (já usado hoje em `AgendaPage.tsx`).

Nenhuma violação identificada. Nenhuma entrada necessária em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/178-agenda-multiplas-visualizacoes/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command) — sem contratos novos, ver README
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/apps/internal/src/
├── pages/
│   └── AgendaPage.tsx            # MODIFICADO — orquestra as 3 visões + toolbar, estado na URL
├── components/
│   ├── CalendarGrid.tsx          # MODIFICADO — clique no dia navega para visão Dia (FR-006/007)
│   ├── AgendaToolbar.tsx         # NOVO — seletor Mês/Dia/Lista + ‹/Hoje/› + título dinâmico
│   ├── DayTimelineView.tsx       # NOVO — grade 00:00–23:00, posicionamento + colunas de overlap
│   └── AgendaListView.tsx        # NOVO — feed agrupado por dia
└── lib/
    ├── agenda.ts                 # INTOCADO — useAgenda/useAgendaDia já cobrem a necessidade
    ├── eventCategory.ts          # INTOCADO — paleta/categorias reaproveitadas nas 3 visões
    └── agendaLayout.ts           # NOVO — função pura de cálculo de posição/overlap (testável em isolado)
```

**Structure Decision**: Feature inteiramente dentro de `frontend/apps/internal` (Web application
já existente, sem novo projeto). Backend (`app/api/agenda.py`, `app/api/agenda_read.py`)
permanece intocado — nenhum diretório novo no backend. A lógica de cálculo de sobreposição de
horários fica isolada em `lib/agendaLayout.ts` (função pura, sem JSX) para poder ser verificada
independentemente dos componentes visuais.

## Complexity Tracking

*Nenhuma violação de constituição identificada — seção não aplicável.*
