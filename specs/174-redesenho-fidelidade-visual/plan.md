# Implementation Plan: Redesenho e Fidelidade Visual das Telas Principais (FASE B)

**Branch**: `174-redesenho-fidelidade-visual` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/174-redesenho-fidelidade-visual/spec.md`

## Summary

Redesenhar as 3 telas de uso diário do beta React (Dashboard, Agenda, Talentos) para recuperar a
fidelidade visual do sistema Jinja clássico, consumindo o design system entregue na 173
(`PageHeader`/`DenseCard`/`MetricBadge`/tokens): donuts de progresso + painéis de tarefas por
setor + painel "Performance" (SUPERADMIN) no Dashboard; grade mensal de calendário com blocos
coloridos por categoria na Agenda; mosaico de fotos grandes com badges de medida em Talentos.
Uma passada leve de alinhamento (`PageHeader`/`DenseCard`) nas demais subpáginas fecha o escopo.
O backend ganha apenas uma extensão aditiva: `/api/dashboard` recebe parâmetros opcionais de
período (`perf_range`/`perf_start`/`perf_end`) e uma seção `performance` na resposta, extraindo
para `dashboard_service.py` a lógica hoje só existente (duplicada) na view Jinja `home()`
(`app/__init__.py`) — mesma fonte única já usada por casting/figurino/financeiro.

## Technical Context

**Language/Version**: TypeScript 5.x / React 18 (frontend); Python 3.12 / Flask (backend)

**Primary Dependencies**: Tailwind CSS 3, TanStack Query 5, framer-motion, `@manto/ui`
(`PageHeader`, `DenseCard`, `MetricBadge`, `Card`, `Skeleton`, `Button`) — **nenhuma dependência
nova**: donuts em CSS puro (`conic-gradient`), grade de calendário em CSS grid, mosaico em CSS
grid. Recharts avaliado e descartado (ver research.md).

**Storage**: nenhuma mudança de schema — extensão aditiva do endpoint `/api/dashboard`
(query params + campo novo na resposta), sem novo modelo.

**Testing**: script de verificação funcional com test client Flask contra `manto_local`
(Postgres) cobrindo `/api/dashboard` com/sem `perf_range` e papéis distintos; `npx tsc --noEmit`
+ `npm run build` no `frontend/apps/internal`; conferência visual em viewport desktop (1440px) e
mobile (375px) via `npm run dev:internal`.

**Target Platform**: web (desktop + mobile ≥320px)

**Project Type**: web (SPA React + API Flask)

**Performance Goals**: nenhuma requisição bloqueante nova além da já existente
(`/api/dashboard`, `/api/agenda`, `/api/talents`); grade de calendário e mosaico renderizam a
partir de dados já paginados/mensais — sem N+1 novo no backend.

**Constraints**: zero regressão funcional nas 3 telas e nas ~30 subpáginas tocadas na User
Story 4; `prefers-reduced-motion` respeitado; sem CSS solto (só Tailwind + tokens do preset da
173); painel Performance só para papel real SUPERADMIN (nunca durante impersonação — mesma
regra do `is_superadmin = _is_real_superadmin(user) and not impersonate` já usada em
`dashboard_service.py`).

**Scale/Scope**: 3 componentes visuais novos em `frontend/apps/internal` (donut, grade de
calendário, mosaico de talentos — específicos do app internal, não promovidos a `@manto/ui`
nesta fase por serem compostos com dados/roteamento do app), 1 endpoint estendido
(`/api/dashboard`), 1 função nova em `dashboard_service.py` (`compute_performance`), ~30
subpáginas com ajuste de alinhamento (User Story 4).

## Constitution Check

*GATE: aprovado. Re-checado após Phase 1 — sem violações.*

- **I. Reutilizar antes de criar** ✅ — `compute_performance`/`compute_comercial_pending` são
  extraídos de `app/__init__.py::home()` para `dashboard_service.py` (fonte única), removendo a
  duplicação que hoje existe só na view Jinja; grade de calendário e mosaico reusam
  `useAgenda`/`useTalentDirectory` e os tipos `EventoResumo`/`TalentSummary` já existentes, sem
  novo hook de busca.
- **II. Padrões de código** ✅ — TS estrito sem `any`; novos componentes com props tipadas;
  `compute_performance` com type hints/docstring Google style.
- **III. API First** ✅ — extensão de `/api/dashboard` é JSON puro, RBAC validado por função
  (não decorator), como o resto da API.
- **IV. Não quebrar o que funciona** ✅ — `home()` (Jinja) passa a chamar as mesmas funções
  extraídas em vez de duplicar a query — paridade obrigatória verificada nos dois lados;
  `tsc`/build/verificação funcional antes do merge.
- **V. UI/UX com feedback** ✅ — skeleton nos 3 componentes novos durante loading; nenhum botão
  morto (ações de aprovar/rejeitar/colapsar painel já existentes preservadas).
- **VII. BRL** ✅ — "Entrada total" do Performance usa `formatBRL` (`@manto/money`), fonte única.
- **VIII. Mobile-first** ✅ — grade de calendário e mosaico com breakpoints Tailwind, conferidos
  em 375px antes de "pronto".
- **IX. Movimento com propósito** ✅ — entrada dos donuts/grade/mosaico com framer-motion,
  respeitando `useReducedMotion()`.

## Project Structure

### Documentation (this feature)

```text
specs/174-redesenho-fidelidade-visual/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── dashboard-performance.md   # Extensão aditiva de /api/dashboard
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── __init__.py                     # home(): passa a chamar compute_performance/
│                                    # compute_comercial_pending em vez de duplicar a query
└── api/
    ├── dashboard.py                 # aceita query params perf_range/perf_start/perf_end
    └── dashboard_service.py         # + compute_performance(), + compute_comercial_pending(),
                                      # build_dashboard_summary() ganha "performance"/"comercial"

frontend/apps/internal/src/
├── components/
│   ├── DonutChart.tsx               # NOVO — donut CSS puro (percentual + label central)
│   ├── SectorPanel.tsx              # NOVO — painel colapsável por setor (badge urgência)
│   ├── CalendarGrid.tsx             # NOVO — grade mensal (recebe EventoResumo[] + ym)
│   └── TalentMosaic.tsx             # NOVO — grid de fotos grandes (recebe TalentSummary[])
├── lib/
│   ├── dashboard.ts                 # NOVO — useDashboard já existe? senão, tipos + hook aqui
│   │                                  (Performance: novos campos em DashboardSummary)
│   └── eventCategory.ts             # NOVO — mapa event_type → cor/rótulo (paridade com
│                                      # event_detail.html: R&I/RI, SHOW, CORP, VM, SOCIAL,
│                                      # ENSAIO, default)
└── pages/
    ├── DashboardPage.tsx             # redesenho: donuts + SectorPanel + Performance
    ├── AgendaPage.tsx                # redesenho: CalendarGrid no lugar da lista por dia
    ├── TalentsListPage.tsx           # redesenho: TalentMosaic no lugar do card horizontal
    └── (demais ~30 páginas)          # US4 — troca de cabeçalho/estatística solta por
                                       # PageHeader/DenseCard onde ainda não adotado
```

**Structure Decision**: `DonutChart`/`SectorPanel`/`CalendarGrid`/`TalentMosaic` ficam locais a
`frontend/apps/internal` (não promovidos a `@manto/ui`) porque cada um é específico do domínio
desta tela (formato de dado, regras de cor por `event_type`, regras de urgência por evento) —
promover exigiria uma API genérica prematura (YAGNI); se a FASE C precisar de donut/grade em
outro app, promove-se então. O backend segue o padrão dos blueprints migrados: `home()`
(Jinja) e a API dividem a mesma função `*_ops`/`*_service`, nunca duas versões da mesma query.

## Decisões-chave (resumo do research.md)

1. **Donuts em CSS puro, não Recharts** — o Jinja já resolve isso com uma única `div` +
   `conic-gradient` via custom property (`--p`); replicar em Tailwind/CSS evita adicionar uma
   dependência de ~90kb para 2 gráficos de 1 série cada. Recharts fica reservado para o dia em
   que o Dashboard precisar de gráficos multi-série reais (ex.: DRE) — não é o caso aqui.
2. **"Distribuição financeira/status" do pedido original = painel Performance do Jinja** —
   investigação em `home.html`/`app/__init__.py` mostrou que o Jinja clássico não tem gráfico de
   distribuição financeira na home; o que existe (e será restaurado) é o painel "Performance"
   (SUPERADMIN): seletor de período + casting/figurino done/total + "Entrada total" (soma de
   cachês). Fidelidade > invenção de uma métrica nova.
3. **Extensão aditiva de `/api/dashboard`**: query params opcionais `perf_range` (`7`|`30`|
   `custom`, default `7`), `perf_start`/`perf_end` (ISO date, só para `custom`); resposta ganha
   `performance: {..} | null` (só para papel real SUPERADMIN) — replica exatamente
   `perf_casting_total/done`, `perf_figurino_total/done`, `perf_money` de `app/__init__.py`.
   Documentado em `contracts/dashboard-performance.md`.
4. **Painel Comercial**: escopo desta fatia cobre só "cobranças pendentes" (saldo em aberto por
   evento com severidade `atrasado`/`vencido`/`urgent`/`warn`) — a mesma lógica de
   `pending_payments` hoje em `home()`. Reembolsos pendentes e pendências de formulário
   (`form_responses_sem_cliente`/`precisam_revisao`) ficam fora desta fatia por serem paineis
   adicionais de baixo uso diário (documentado como Assumption/stretch); podem entrar em
   iteração futura sem novo redesenho estrutural.
5. **Categoria de evento na Agenda**: cor por `event_type` reaproveitando o mapa já usado em
   `event_detail.html` (R&I/RI → azul, SHOW → dourado, CORP → cinza, VM → azul, SOCIAL → verde,
   ENSAIO → cor própria [laranja, como o prefixo "🟧 ENSAIO" sugere], default → cinza).
6. **Grade de calendário usa `by_day` já existente** — `AgendaMes.by_day: Record<string,
   number[]>` já mapeia dia → ids de evento; a grade só precisa indexar `events` por dia (mesmo
   dado que `AgendaPage.tsx` já agrupa hoje, só que em formato de grade em vez de lista).
7. **Mosaico de Talentos reaproveita `useTalentDirectory` sem mudança de hook/endpoint** — é
   puramente uma troca de `TalentCard` (avatar 64px + linha) por um card de mosaico (foto grande
   + badges sobrepostos), mantendo toda a barra de busca/filtros/paginação atual.
8. **Painéis colapsáveis do Dashboard**: estado local (`useState`) por painel, sem persistência
   — paridade suficiente com o comportamento do Jinja (`toggleSector`, também sem persistência).

## Complexity Tracking

Sem violações da constituição — tabela não aplicável.
