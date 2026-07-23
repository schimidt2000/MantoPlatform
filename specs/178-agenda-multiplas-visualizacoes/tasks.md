---

description: "Task list for feature 178 — Agenda com múltiplas visualizações (Mês, Dia, Lista)"
---

# Tasks: Agenda com múltiplas visualizações (Mês, Dia, Lista)

**Input**: Design documents from `/specs/178-agenda-multiplas-visualizacoes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/README.md, quickstart.md

**Tests**: Não há suíte automatizada de frontend no projeto. Verificação é via `tsc --noEmit`,
`npm run build` e checagem visual manual/Playwright (pedidos explicitamente pelo usuário) — sem
tasks de teste unitário.

**Organization**: Tarefas agrupadas por user story do spec.md, em ordem de prioridade
(US1 P1, US3 P1, US2 P2, US4 P2, US5 P3). 100% frontend — nenhum arquivo de backend é tocado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência entre si)
- **[Story]**: A qual user story esta tarefa pertence (US1..US5)
- Caminhos de arquivo exatos em cada descrição

## Path Conventions

Web app existente — só o lado frontend: `frontend/apps/internal/src/`.

---

## Phase 1: Setup

**Purpose**: Nenhuma inicialização de projeto necessária — app React já existe e roda
(`npm run dev:internal`). Fase reduzida a confirmar que o ambiente está pronto.

- [X] T001 Confirmar que `frontend/apps/internal` builda hoje sem erros antes de tocar em código: `cd frontend/apps/internal && npx tsc --noEmit && npm run build` (baseline, sem alterações)

**Checkpoint**: Baseline verde confirmada — qualquer erro novo depois disso é desta feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Estado de visão/data compartilhado por todas as 3 visões (view mode + data de
referência sincronizados com a URL) e os helpers de data/rótulo que Mês, Dia e Lista usam.
Nenhuma user story pode ser concluída sem isso.

**⚠️ CRITICAL**: Bloqueia todas as user stories abaixo.

- [X] T002 [P] Criar `frontend/apps/internal/src/lib/agendaDates.ts` (NOVO) com: tipo `AgendaViewMode = "month" | "day" | "list"`, `shiftDay(date: string, delta: number): string`, `shiftMonth(ym: string, delta: number): string`, `dayLabel(date: string): string` (ex.: "25 de julho de 2026", capitalizado), reaproveitando a lógica de `shiftYm`/`monthLabel` já existente em `AgendaPage.tsx` (mover para cá, não duplicar)
- [X] T003 [P] Criar `frontend/apps/internal/src/lib/agendaLayout.ts` (NOVO) com o tipo `AgendaLayoutBlock` (ver data-model.md) e assinatura exportada `computeDayLayout(events: EventoResumo[]): AgendaLayoutBlock[]` (corpo/algoritmo implementado na Phase 4 — US3; aqui só a fundação para outros arquivos poderem importar o tipo)
- [X] T004 Substituir o `useState<string>(currentYm())` local de `frontend/apps/internal/src/pages/AgendaPage.tsx` por estado `{ view: AgendaViewMode; refDate: string }` sincronizado com `useSearchParams` do React Router (`?view=&date=`), usando os helpers de T002; manter renderização da visão Mês funcionando exatamente como hoje com o novo estado (regressão zero)

**Checkpoint**: Fundação pronta — as 3 user stories de visão podem ser implementadas.

---

## Phase 3: User Story 1 - Alternar entre Mês, Dia e Lista (Priority: P1) 🎯 MVP

**Goal**: Seletor de visualização (Mês/Dia/Lista) + barra de navegação (‹, Hoje, ›) + título
dinâmico, preservando a data de referência ao trocar de visão.

**Independent Test**: Abrir `/agenda`, alternar as 3 opções do seletor e conferir que a tela
troca de layout mantendo a data; conferir que ‹/Hoje/› avança/retrocede/reseta corretamente.

### Implementation for User Story 1

- [X] T005 [US1] Criar `frontend/apps/internal/src/components/AgendaToolbar.tsx` (NOVO): seletor de 3 opções (Mês/Dia/Lista) com opção ativa destacada, botões ‹/Hoje/›, título dinâmico via `dayLabel`/`monthLabel` conforme a visão ativa — props tipadas (`view`, `refDate`, `onViewChange`, `onNavigate`), sem lógica de fetch
- [X] T006 [US1] Integrar `AgendaToolbar` em `frontend/apps/internal/src/pages/AgendaPage.tsx` no lugar dos botões ‹/› atuais dentro do `PageHeader`; `onNavigate` chama `shiftDay`/`shiftMonth` conforme `view` ativa (um dia na visão Dia, um mês nas visões Mês/Lista); "Hoje" volta `refDate` para a data real do sistema
- [X] T007 [US1] Renderizar condicionalmente por `view` em `AgendaPage.tsx`: `"month"` → `CalendarGrid` (já existente, comportamento intocado); `"day"`/`"list"` → placeholder simples (`<p className="py-10 text-center text-muted">Em construção</p>`) a ser substituído nas Phases 4 e 6
- [X] T008 [US1] Envolver a troca de visão/período em transição Framer Motion (150–350ms, `easeOut`) respeitando `useReducedMotion()` — já importado em `AgendaPage.tsx`, reaproveitar o padrão do `motion.div` existente (Princípio IX)
- [X] T009 [US1] Verificação manual (quickstart.md #1–#2): trocar Mês→Dia→Lista→Mês sem resetar a data; ‹/Hoje/› corretos nas 3 visões

**Checkpoint**: Seletor e navegação funcionam; Dia/Lista ainda são placeholders — MVP de
navegação entregue.

---

## Phase 4: User Story 3 - Visão Dia em linha do tempo com sobreposição (Priority: P1)

**Goal**: Linha do tempo 00:00–23:00 com eventos posicionados por horário e sobreposições lado
a lado, estilo Google Agenda.

**Independent Test**: Carregar a visão Dia de uma data com eventos conhecidos e conferir
posicionamento vertical correto e blocos sobrepostos lado a lado sem colidir.

### Implementation for User Story 3

- [X] T010 [P] [US3] Implementar o algoritmo de cluster/coluna em `computeDayLayout` (`frontend/apps/internal/src/lib/agendaLayout.ts`, fundação criada em T003): agrupar eventos por sobreposição transitiva de `[start_at, end_at)`, calcular `topPct`/`heightPct` relativos a 00:00–24:00 (duração mínima de 1h para eventos sem `end_at`), truncar `heightPct` ao final do dia para eventos que passam da meia-noite, atribuir `column`/`columnCount` por cluster
- [X] T011 [US3] Criar `frontend/apps/internal/src/components/DayTimelineView.tsx` (NOVO): grade vertical de horas (00:00–23:00) com linhas de hora, blocos posicionados via `computeDayLayout` (largura `100% / columnCount`, offset por `column`), cada bloco exibindo categoria (`eventCategory`), título, horário início–fim e local; seção separada no topo para eventos sem `start_at`/`end_at`; bloco navega para `/events/:id` ao clicar
- [X] T012 [US3] Consumir `useAgendaDia(refDate)` dentro de `DayTimelineView` (ou receber via prop de `AgendaPage.tsx`) com estados de loading (`Skeleton`), erro (mensagem pt-BR) e vazio ("Nenhum evento neste dia."), no mesmo padrão já usado pela visão Mês
- [X] T013 [US3] Substituir o placeholder de `view === "day"` em `AgendaPage.tsx` (de T007) por `<DayTimelineView />`
- [X] T014 [US3] Verificação manual (quickstart.md #4): evento único posicionado corretamente; 2+ eventos sobrepostos lado a lado e legíveis; evento sem horário na seção separada; clique no bloco navega para o detalhe

**Checkpoint**: Mês + Dia funcionais e independentes entre si.

---

## Phase 5: User Story 2 - Clicar num dia da grade mensal (Priority: P2)

**Goal**: Clicar no número do dia ou em área vazia da célula da grade mensal abre a visão Dia
daquela data; clique num evento continua indo para o detalhe.

**Independent Test**: Na visão Mês, clicar no número "25" (fora de badges) leva à visão Dia de
25; clicar num badge de evento continua abrindo `/events/:id`.

### Implementation for User Story 2

- [X] T015 [US2] Adicionar prop `onDayClick?: (dateKey: string) => void` a `CalendarGrid`/`DayCell` em `frontend/apps/internal/src/components/CalendarGrid.tsx`: `onClick` na `div` da célula (fora dos `<Link>` de evento e do botão "+N") chama `onDayClick(cell.key)`
- [X] T016 [US2] Passar `onDayClick` de `AgendaPage.tsx` para `CalendarGrid`, definido para: `setView("day")` + `setRefDate(dateKey)` (usa o estado de T004)
- [X] T017 [US2] Verificação manual (quickstart.md #3): clique no número do dia e em célula vazia abrem a visão Dia correta; clique em badge de evento não muda de visão, vai direto ao detalhe

**Checkpoint**: Mês, Dia e a ponte entre eles funcionam de ponta a ponta.

---

## Phase 6: User Story 4 - Visão em Lista (feed cronológico) (Priority: P2)

**Goal**: Feed dos eventos do mês corrente, agrupados por dia, em ordem cronológica, com
horário, badge de categoria, título, local e botão "Abrir".

**Independent Test**: Carregar a visão Lista de um mês com eventos em múltiplos dias e conferir
agrupamento por dia em ordem cronológica, com todos os campos exigidos por item.

### Implementation for User Story 4

- [X] T018 [P] [US4] Criar `frontend/apps/internal/src/components/AgendaListView.tsx` (NOVO): recebe `events: EventoResumo[]` (do `useAgenda(ym)` já carregado por `AgendaPage.tsx`), agrupa por dia (`start_at.slice(0,10)`) em ordem cronológica, eventos sem `start_at` na seção "Sem data" já existente (paridade com a visão Mês); cada item mostra horário (ou "sem horário definido"), badge (`eventCategory`), título, local e botão "Abrir" alinhado à direita, navegando para `/events/:id`
- [X] T019 [US4] Substituir o placeholder de `view === "list"` em `AgendaPage.tsx` (de T007) por `<AgendaListView events={events} />`, reaproveitando o mesmo `agenda.data.events` já buscado por `useAgenda(ym)` — sem novo fetch
- [X] T020 [US4] Verificação manual (quickstart.md #5): agrupamento por dia correto, ordem cronológica, botão "Abrir" navega, evento sem horário aparece corretamente

**Checkpoint**: As 3 visões (Mês, Dia, Lista) e a navegação entre elas estão completas.

---

## Phase 7: User Story 5 - Layout fluido e responsivo (Priority: P3)

**Goal**: Container de largura total em telas widescreen; as 3 visões legíveis e sem rolagem
horizontal da página em viewport mobile (320–375px).

**Independent Test**: Redimensionar a janela entre ~1920px e 320–375px em cada uma das 3
visões e conferir ausência de rolagem horizontal indevida, texto cortado ou espaço
desperdiçado.

### Implementation for User Story 5

- [X] T021 [US5] Trocar `max-w-5xl` por `w-full` no container raiz de `frontend/apps/internal/src/pages/AgendaPage.tsx`, mantendo `p-4 sm:p-6`
- [X] T022 [P] [US5] Ajuste responsivo em `DayTimelineView.tsx` para 320–375px: largura mínima legível por coluna de bloco, rótulos de hora compactos, sem rolagem horizontal da página (rolagem vertical normal)
- [X] T023 [P] [US5] Ajuste responsivo em `AgendaListView.tsx` para 320–375px: item em coluna única, botão "Abrir" com alvo de toque confortável
- [X] T024 [US5] Verificação manual em 1920px+ e 320–375px nas 3 visões (quickstart.md #6)

**Checkpoint**: Todas as 5 user stories completas e verificadas.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Portões de qualidade finais antes do commit/merge (checklist da constituição).

- [X] T025 [P] Rodar `npx tsc --noEmit` em `frontend/apps/internal` e corrigir qualquer erro de tipo introduzido pela feature
- [X] T026 [P] Rodar `npm run build` em `frontend/apps/internal` e corrigir qualquer erro de build
- [X] T027 Verificação visual via Playwright: capturar Mês/Dia/Lista em desktop widescreen (1920×1080) e mobile (375×812), conferir ausência de regressão visual e de rolagem horizontal
- [X] T028 Atualizar `docs/changelog.html` com uma entrada em português simples descrevendo a nova Agenda (Mês/Dia/Lista) e republicar no mesmo link/artifact já existente
- [X] T029 Rodar a checklist de verificação manual completa de `quickstart.md` de ponta a ponta

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as user stories
- **US1 (Phase 3, P1)**: depende só do Foundational
- **US3 (Phase 4, P1)**: depende do Foundational; usa o placeholder de `view==="day"` criado em US1 (T007), então na prática roda depois de T007, mas é conceitualmente independente (o componente `DayTimelineView` pode ser testado isolado com dados de fixture antes mesmo de existir a `AgendaToolbar`)
- **US2 (Phase 5, P2)**: depende do Foundational (T004, estado de view/refDate) e da existência da visão Dia (US3, Phase 4) para ter para onde navegar
- **US4 (Phase 6, P2)**: depende do Foundational; usa o placeholder de `view==="list"` (T007)
- **US5 (Phase 7, P3)**: depende de US1, US3 e US4 já existirem (ajusta a largura/responsividade dos componentes que elas criaram)
- **Polish (Phase 8)**: depende de todas as user stories desejadas estarem completas

### Parallel Opportunities

- T002 e T003 (Phase 2) — arquivos diferentes, sem dependência entre si
- T010 (algoritmo de layout) pode começar em paralelo com T005 (toolbar) — arquivos diferentes, T010 só depende do tipo criado em T003
- T018 (AgendaListView) pode ser desenvolvido em paralelo com T010/T011 (Day timeline) — componentes independentes
- T022 e T023 (Phase 7) — arquivos diferentes
- T025 e T026 (Phase 8) — comandos independentes

---

## Parallel Example: Foundational + arranque de US3/US4

```bash
# Fase 2, em paralelo:
Task: "Criar frontend/apps/internal/src/lib/agendaDates.ts com tipos e helpers de data"
Task: "Criar frontend/apps/internal/src/lib/agendaLayout.ts com o tipo AgendaLayoutBlock"

# Depois do Foundational, US3 e US4 podem avançar em paralelo (arquivos distintos):
Task: "Implementar computeDayLayout em lib/agendaLayout.ts"
Task: "Criar components/AgendaListView.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1 (Setup) e Phase 2 (Foundational)
2. Completar Phase 3 (US1) — seletor + navegação funcionando (Dia/Lista como placeholder)
3. **PARAR e VALIDAR**: testar US1 isoladamente conforme seu Independent Test
4. A partir daqui, US3 (Dia) é o próximo incremento de maior valor (também P1)

### Entrega Incremental

1. Setup + Foundational → base pronta
2. US1 → seletor/navegação funcionando (placeholder em Dia/Lista) → validar
3. US3 → visão Dia completa (o ganho funcional principal pedido) → validar
4. US2 → ponte clique-no-dia→Dia → validar
5. US4 → visão Lista completa → validar
6. US5 → layout fluido/responsivo nas 3 visões → validar
7. Polish → tsc/build/Playwright/changelog → commit + merge + push

### Notes

- [P] = arquivos diferentes, sem dependência
- Cada user story deve ficar completável e testável de forma independente
- Sem tasks de teste automatizado (não solicitado; projeto não tem suíte de frontend) —
  verificação é manual/visual conforme quickstart.md e portões da constituição
- Commit após cada task ou grupo lógico de tasks, mas o commit/merge/push final para `main`
  só acontece ao fim da Phase 8, por instrução do usuário
