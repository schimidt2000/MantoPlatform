# Tasks: Redesenho e Fidelidade Visual das Telas Principais (FASE B)

**Input**: Design documents from `specs/174-redesenho-fidelidade-visual/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
`contracts/dashboard-performance.md`

**Organização**: tarefas agrupadas por user story para permitir implementação e teste
independentes. Verificação funcional automatizada para o backend (test client contra
`manto_local`); frontend valida por `tsc`/build + conferência no app real (desktop + 375px).

## Phase 1: Setup — mapa de categorias de evento

**Purpose**: utilitário compartilhado pela Agenda (US2), base sem dependência de dado remoto

- [X] T001 [P] Criar `frontend/apps/internal/src/lib/eventCategory.ts` — `eventCategory(event_type: string): { label: string; bg: string; fg: string }` com paridade ao mapa de `app/templates/event_detail.html` (`R&I`/`RI` → azul, `SHOW` → roxo/accent — achado real: `.badge-gold` em `app/static/style.css` renderiza `--accent`/roxo, não dourado, nome de classe legado —, `CORP` → cinza, `VM` → azul, `SOCIAL` → verde, `ENSAIO`/default → cinza neutro, sem entrada própria no mapa Jinja), usando tokens Tailwind do preset da 173 (sem hex solto)

**Checkpoint**: utilitário pronto — não bloqueia nenhuma story, mas é consumido por US2

---

## Phase 2: Foundational — extensão do contrato do Dashboard

**Purpose**: `/api/dashboard` passa a expor `comercial`/`performance` (bloqueia US1)

- [X] T002 Criar `compute_comercial_pending(cutoff: datetime) -> list[dict]` em `app/api/dashboard_service.py`, extraindo a lógica de `pending_payments` hoje inline em `app/__init__.py::home()` (linhas ~578–643: saldo por evento, severidade `atrasado`/`vencido`/`urgent`/`warn`/`info`, ordenação por `_SEVERITY_ORDER`) — type hints + docstring Google style
- [X] T003 Criar `compute_performance(start_dt: datetime | None, end_dt: datetime | None) -> dict` (calcula `exclude_ensaios` internamente) + `resolve_performance_period(perf_range, perf_start, perf_end)` em `app/api/dashboard_service.py`, extraindo a lógica de `perf_casting_total/done`, `perf_figurino_total/done`, `perf_money` hoje inline em `app/__init__.py::home()` (linhas ~528–576)
- [X] T004 Estender `build_dashboard_summary()` em `app/api/dashboard_service.py`: aceitar `perf_range`/`perf_start`/`perf_end` opcionais; adicionar `"comercial"` (via T002, visível a `COMERCIAL`/`FINANCEIRO`/SUPERADMIN) e `"performance"` (via T003, **null** salvo para papel real SUPERADMIN sem impersonação — reusar `is_superadmin = _is_real_superadmin(user) and not impersonate` já existente) ao retorno
- [X] T005 Atualizar `GET /api/dashboard` em `app/api/dashboard.py` para ler `request.args.get("perf_range", "7")`/`perf_start`/`perf_end` e repassar a `build_dashboard_summary`; em `perf_range=custom` com datas ausentes/inválidas ou `start > end`, responder `200` com `performance: null` (fallback silencioso, mesmo comportamento do Jinja)
- [X] T006 Atualizar `app/__init__.py::home()` para chamar `compute_comercial_pending`/`compute_performance` em vez de duplicar a query (paridade obrigatória — mesmo resultado que antes)
- [X] T007 [P] Criar `specs/174-redesenho-fidelidade-visual/verify_174.py` — test client contra `manto_local` (requests FORA de `app_context`): login por papel (CASTING, FIGURINO, FINANCEIRO, COMERCIAL, SUPERADMIN) → `GET /api/dashboard` sem parâmetro e com `perf_range=30`/`perf_range=custom` (válido e inválido) → conferir presença/ausência de `comercial`/`performance` por papel → SUPERADMIN com "Ver como" ativo → `performance` ausente → comparar números com os já existentes em `compute_casting_tasks`/`compute_figurino_tasks` para o mesmo estado de banco

**Checkpoint**: `/api/dashboard` estendido e coberto por verificação — pronto para US1

---

## Phase 3: User Story 1 — Dashboard com indicadores visuais e tarefas por setor (P1) 🎯 MVP

**Goal**: donuts de Casting/Figurino, painéis colapsáveis por setor com badges de urgência, e
painel Performance (SUPERADMIN) — paridade com a home Jinja clássica

**Independent Test**: logar com cada papel e comparar visualmente com a home Jinja (mesmos
números, mesmo agrupamento, mesmas badges)

- [X] T008 [P] [US1] Atualizar `frontend/apps/internal/src/lib/types.ts` (ou arquivo de tipos do dashboard já existente) com os campos novos de `DashboardSummary` (`comercial`, `performance`) descritos em `data-model.md`
- [X] T009 [P] [US1] Criar `frontend/apps/internal/src/components/DonutChart.tsx` — donut CSS puro (`conic-gradient`), props `{ label: string; done: number; total: number }`; achado real: `.donut` em `app/static/style.css` usa sempre verde (concluído)/vermelho-suave (restante), não uma cor por setor — cores fixas replicadas em vez de um prop `tone`; percentual central, fração abaixo, `total === 0` renderiza 0% sem erro, anima o preenchimento respeitando `useReducedMotion()`
- [X] T010 [P] [US1] Criar `frontend/apps/internal/src/components/SectorPanel.tsx` — painel colapsável (`useState` local), cabeçalho com badge de contagem de pendentes ou "Tudo em dia ✓" quando zero, corpo com lista de itens; suporte a badge de urgência por item (`URGENTE` ≤2 dias, `Nd` ≤7 dias, calculado a partir de `start_at`)
- [X] T011 [US1] Reescrever `frontend/apps/internal/src/pages/DashboardPage.tsx`: donuts de Casting/Figurino via `DonutChart`; `SectorPanel` para Casting (com urgência), Figurino, Comercial (`pending_payments`, badge de severidade), Contas recorrentes (já existente, migrar para `SectorPanel`); painel de Performance (SUPERADMIN real) com seletor de período (7/30/custom com inputs de data) consumindo os novos parâmetros de `/api/dashboard`, exibindo casting/figurino done-total e "Entrada total" via `formatBRL`; manter skeleton/erro via TanStack Query
- [X] T012 [US1] Verificação: rodar `verify_174.py` (Phase 2) + subir app real (`.\scripts\db\run-local.ps1` + `npm run dev:internal`) e comparar visualmente Dashboard React vs. home Jinja para cada papel, incluindo "Ver como"

**Checkpoint**: Dashboard com paridade visual — pode ser demonstrado isoladamente

---

## Phase 4: User Story 2 — Agenda em grade mensal de calendário (P1)

**Goal**: grade de calendário do mês com blocos coloridos por categoria, substituindo a lista
atual, sem tocar backend/RBAC

**Independent Test**: navegar por um mês com eventos variados; blocos com cor certa, dia atual
destacado, clique abre o evento correto

- [X] T013 [US2] Criar `frontend/apps/internal/src/components/CalendarGrid.tsx` — recebe `events: EventoResumo[]` + `ym: string`; monta semanas completas (dias adjacentes esmaecidos), destaca o dia atual, indexa eventos por dia (mesma técnica de `groups` já usada em `AgendaPage.tsx`), renderiza blocos coloridos via `eventCategory()` (T001) com indicador "+N" quando exceder o espaço da célula, cada bloco navega para `/events/<id>`
- [X] T014 [US2] Reescrever `frontend/apps/internal/src/pages/AgendaPage.tsx`: substituir a lista agrupada por dia por `CalendarGrid`, mantendo `useAgenda(ym)`, navegação de mês (‹ ›) e botão "Novo evento" (RBAC inalterado) no `PageHeader`
- [X] T015 [US2] Ajustar `CalendarGrid` para viewport mobile (<768px): grade com scroll horizontal controlado ou visão compacta, sem overflow horizontal da página
- [X] T016 [US2] Verificação: `npx tsc --noEmit` + `npm run build` (internal); conferir no app real um mês com eventos de tipos variados (cores corretas, clique abre evento, navegação de mês preserva loading/erro) em desktop e 375px

**Checkpoint**: Agenda em grade mensal funcionando — independente do Dashboard

---

## Phase 5: User Story 3 — Banco de Talentos em mosaico de fotos (P2)

**Goal**: mosaico de fotos grandes com badges de medida, preservando toda a funcionalidade
existente (busca/filtros/paginação/aprovação)

**Independent Test**: abrir talentos ativos, conferir grid de fotos grandes com badges
legíveis; busca/filtros continuam funcionando; aprovar/rejeitar em Pendentes intacto

- [X] T017 [US3] Criar `frontend/apps/internal/src/components/TalentMosaic.tsx` — recebe `talents: TalentSummary[]` + `isPending: boolean`; grid responsivo (5–6 colunas desktop, 2 mobile, 1 em telas muito estreitas), card com foto de rosto em destaque (proporção retrato, placeholder quando sem foto), nome truncado com reticências, badges de medida (altura/tamanho/calçado) sempre visíveis, indicador de `warning_level` sobreposto, botões Aprovar/Rejeitar quando `isPending`
- [X] T018 [US3] Substituir a renderização de cards em `frontend/apps/internal/src/pages/TalentsListPage.tsx` por `TalentMosaic`, mantendo busca, filtros, paginação, alternância Ativos/Pendentes e `useApproveTalent`/`useRejectTalent` inalterados
- [X] T019 [US3] Verificação: `npx tsc --noEmit` + `npm run build` (internal); conferir no app real busca/filtros/paginação/aprovação/rejeição sobre o novo mosaico, em desktop (≥15 talentos acima da dobra em 1440px) e mobile 375px

**Checkpoint**: Talentos em mosaico — independente das demais stories

---

## Phase 6: User Story 4 — Alinhamento de densidade nas demais subpáginas (P3)

**Goal**: subpáginas fora do escopo principal adotam `PageHeader`/`DenseCard`/`MetricBadge`
onde ainda usam cabeçalho/estatística solta

**Independent Test**: amostrar 5 subpáginas de setores diferentes e confirmar uso dos
componentes do design system, sem regressão de fluxo

- [X] T020 [US4] Varrer `frontend/apps/internal/src/pages/` (fora de Dashboard/Agenda/Talentos) — 9 páginas sem `PageHeader`: `EventDetailPage`, `FigurinoFormPage`, `ClientDetailPage`, `AdminUserEditPage`, `RevisaoAssetPage`, `RevisaoSpacePage`, `TalentDetailPage`, `AdminCatalogoFormPage` (+ `LoginPage`, fora do shell por design — 173)
- [X] T021 [US4] Adotar `PageHeader` em 5 delas (amostra de setores distintos): `EventDetailPage` (evento), `FigurinoFormPage` (figurino), `ClientDetailPage` (clientes), `AdminUserEditPage` (admin), `RevisaoSpacePage` (revisão de mídia) — cabeçalho + ações movidas para o slot `actions`, sem alterar fluxo/endpoints. `TalentDetailPage`/`RevisaoAssetPage`/`AdminCatalogoFormPage` ficaram fora desta amostra (header com avatar/composição própria — ver Assumptions do plan.md: alinhamento é amostral, não integral)
- [X] T022 [US4] Verificação: `npx tsc --noEmit` + `npm run build` (internal); amostrar as 5 páginas ajustadas no app real e confirmar ausência de regressão funcional

**Checkpoint**: FASE B completa — todas as telas principais e uma amostra de subpáginas com
fidelidade visual restaurada

---

## Phase 7: Polish & Cross-Cutting

- [X] T023 `ruff check app/` limpo nos arquivos tocados (`dashboard_service.py`, `dashboard.py`, `__init__.py`); ESLint/format nos TS/TSX novos (`DonutChart`, `SectorPanel`, `CalendarGrid`, `TalentMosaic`, `eventCategory`); revisar ausência de CSS solto/estilos inline
- [X] T024 Atualizar `docs/changelog.html` (entrada: Dashboard com donuts/tarefas por setor/Performance, Agenda em grade mensal, Talentos em mosaico de fotos) e republicar no MESMO artifact existente
- [ ] T025 Commit atômico final, merge em `main` e push (stage explícito, nunca `git add -A`)

---

## Dependencies & Execution Order

- **Phase 1 (T001)** → **US2** (Agenda consome `eventCategory`); não bloqueia US1/US3.
- **Phase 2 (T002–T007)** → **US1** (Dashboard consome a extensão do contrato); não bloqueia
  US2/US3.
- **US1 (Phase 3)**: MVP mais visível — depende só de Phase 2.
- **US2 (Phase 4)**: independente de US1/US3 — depende só de T001 (Phase 1).
- **US3 (Phase 5)**: independente de US1/US2/US4 — nenhuma dependência de fase anterior além
  dos tipos já existentes.
- **US4 (Phase 6)**: independente, mas idealmente feita por último (evita retrabalho se US1–3
  mudarem convenções de componente).
- **Parallel opportunities**: T001 ∥ T002–T007 (frentes diferentes); Phase 3 ∥ Phase 4 ∥
  Phase 5 (arquivos/páginas distintos, sem dependência cruzada); T008 ∥ T009 ∥ T010 dentro da
  US1.

## Implementation Strategy

MVP = Phase 1 + Phase 2 + Phase 3 (Dashboard com paridade visual — a tela mais visitada).
Agenda (US2) e Talentos (US3) podem ser entregues em qualquer ordem depois, por serem
totalmente independentes entre si e do Dashboard. US4 fecha a fatia. Cada checkpoint = commit
atômico com builds verdes (Princípio IV).
