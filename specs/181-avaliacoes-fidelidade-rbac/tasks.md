---

description: "Task list for feature 181 — Resumo das Avaliações (fidelidade visual + RBAC)"
---

# Tasks: Resumo das Avaliações — fidelidade visual e RBAC de anonimato

**Input**: Design documents from `/specs/181-avaliacoes-fidelidade-rbac/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ratings-api.md, quickstart.md

**Tests**: Verificação funcional automatizada é obrigatória pelo portão de qualidade do projeto
(constituição, não pela spec) — incluída como tarefa de polish/verificação, não como TDD story-by-story.

**Organization**: Tasks agrupadas por user story (spec.md). Como a implementação é essencialmente
uma reescrita de um único arquivo de página React, as tasks de cada user story tocam
`AvaliacaoCastingPage.tsx` em seções lógicas e são sequenciais entre si (não `[P]`) quando tocam o
mesmo arquivo; tasks em arquivos distintos (backend, tipos) são `[P]`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

**Purpose**: Nenhuma inicialização de projeto necessária (app já existe) — apenas confirmar
ambiente de verificação disponível.

- [ ] T001 Confirmar que `manto_local` (Postgres) está acessível e migrado (`python -m flask db heads` com `DATABASE_URL` da cópia local via `scripts/db/run-local.ps1`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Alterações de core reusado por todas as user stories — nenhuma story pode começar
sem isso.

**⚠️ CRITICAL**: Bloqueia todas as user stories abaixo.

- [ ] T002 Adicionar preset `"7d": 7` em `_PERIOD_PRESETS` e `"7d": "última semana"` em `PERIOD_LABELS` em `app/talents/rating_ops.py` (aditivo — não alterar mais nada na função)
- [ ] T003 [P] Adicionar `"7d"` à union de valores aceitos em `RatingsFilters.period` (e, se existir union equivalente de retorno) em `frontend/apps/internal/src/lib/ratings.ts`

**Checkpoint**: Backend e tipos prontos — user stories de UI podem começar.

---

## Phase 3: User Story 4 - Confiar que a autoria respeita RBAC (Priority: P1)

**Goal**: Garantir que o toggle de modo anônimo total só aparece para SUPERADMIN e que a autoria
exibida é sempre exatamente o que a API retorna (nunca decidida no frontend).

**Independent Test**: Logar como não-SUPERADMIN e confirmar ausência do toggle e autoria sempre
"Anônimo"; logar como SUPERADMIN e confirmar toggle funcional.

### Implementation for User Story 4

- [ ] T004 [US4] Em `frontend/apps/internal/src/pages/AvaliacaoCastingPage.tsx`, ao iniciar a reescrita, montar o cabeçalho da página (`PageHeader`) e o container raiz (`w-full px-6 py-6 sm:px-8`, ver US5/T017) com o bloco de privacidade: renderizar o toggle de "modo anônimo total" (`useToggleAnonymousMode`) condicionado estritamente a `query.data.is_superadmin`, com `Button loading={toggleAnon.isPending}` (nunca "morto" ao clique) e texto de estado atual (ativo/inativo)
- [ ] T005 [US4] Garantir que todo componente de exibição de autoria criado nas demais stories (T009, T012) renderiza literalmente `c.author`/`c.author_funcao` vindos da API, sem nenhuma condicional de papel no frontend

**Checkpoint**: RBAC de anonimato correto e isolado — pode ser validado sozinho antes das demais stories.

---

## Phase 4: User Story 1 - Panorama com KPIs e gráficos (Priority: P1)

**Goal**: Restaurar KPIs principais e os 4 painéis de gráficos/rankings do Jinja legado.

**Independent Test**: Com avaliações existentes, abrir a tela sem filtro e ver os 3 KPIs e os 4
painéis (tendência, distribuição, categoria, ranking) com os mesmos números do `/talents/avaliacoes` Jinja.

### Implementation for User Story 1

- [ ] T006 [US1] Linha de KPIs principais em `AvaliacaoCastingPage.tsx`: `DenseCard`/`Card` com nota média geral (estrelas + valor), total de avaliações, eventos avaliados (omitido quando `selected_event`) — usar `recorte_label` como legenda
- [ ] T007 [US1] Painel "Tendência mensal" (barras verticais simples com Tailwind, altura proporcional a `t.avg/5`), visível apenas quando `trend.length >= 2` e sem evento selecionado
- [ ] T008 [US1] Painel "Distribuição das notas" (barras horizontais 5★–1★, largura proporcional a `dist[s]/dist_max`)
- [ ] T009 [US1] Painel "Média por categoria" (uma linha por `by_category`, com estrelas + nota, clicável para `setCat(c.key)`), visível apenas quando `cat` não está ativo
- [ ] T010 [US1] Painel "Melhores eventos vs. Pontos a melhorar" (`best_events`/`worst_events`, cada linha clicável para `setEventId(e.id)`), visível apenas na visão agregada (sem `selected_event`)
- [ ] T011 [US1] Estado vazio (`total === 0`): mensagem clara substituindo os painéis acima, com ação "Limpar filtros" quando `has_filters`

**Checkpoint**: Painel de KPIs/gráficos completo e testável isoladamente (mesmo sem os filtros ricos de US2 — os filtros simples já existentes continuam funcionando).

---

## Phase 5: User Story 2 - Filtros ricos em pills (Priority: P1)

**Goal**: Substituir os dropdowns simples por pills de período (incl. "última semana"), alternância
de modo de data, pills de categoria e dropdown de evento agrupado por mês.

**Independent Test**: Clicar em cada pill/opção e confirmar que os KPIs/listas recalculam e que a
seleção ativa fica destacada.

### Implementation for User Story 2

- [ ] T012 [US2] Barra de período: `Button variant={period===key?"default":"outline"} size="sm"` para Tudo/Última semana("7d")/30 dias/3 meses/12 meses, mais bloco "Personalizado" com dois `Input type="date"` e botão "Aplicar" — ocultar quando `eventId` está definido
- [ ] T013 [US2] Alternância "Filtrar por": dois `Button` (Data do evento / Data da avaliação) ligados a `date_mode`, ocultos quando `eventId` está definido
- [ ] T014 [US2] Pills de categoria: `Button` para Todas/Artista/Som/Figurino/Texto/Coordenação/Maquiagem ligados a `cat`
- [ ] T015 [US2] Dropdown de evento agrupado por mês (`<select>` com `<optgroup>` a partir de `query.data.event_groups`), com ação "Abrir evento" (link) quando `selected_event`
- [ ] T016 [US2] Ação "Limpar filtros" (reseta period/cat/eventId/date_mode para o padrão), visível apenas quando `query.data.has_filters`

**Checkpoint**: Filtros ricos completos — combinam com os painéis de US1 para o fluxo principal da tela.

---

## Phase 6: User Story 3 - Pontos de atenção e comentários (Priority: P2)

**Goal**: Bloco de pontos de atenção com destaque de alerta e bloco de comentários recentes, com
contexto completo (categoria, evento, autor, data).

**Independent Test**: Com uma avaliação de nota 1-2 no recorte, confirmar destaque vermelho e
contexto completo; sem nenhuma, confirmar mensagem positiva.

### Implementation for User Story 3

- [ ] T017 [US3] Bloco "Pontos de atenção": borda/tom de alerta (`border-red`/`bg-red-soft` conforme tokens do projeto) quando `attention.length > 0`, cada item com badge de nota, `cat_label`, autor (+`author_funcao`), evento (clicável para focar, quando não `selected_event`), data e comentário (ou "Sem comentário."); quando vazio, mensagem positiva (ex. "Nenhuma nota baixa no recorte.")
- [ ] T018 [US3] Bloco "Comentários" (mais recentes): lista de `comments` com estrelas, `cat_label`, evento (clicável quando não `selected_event`), data; mensagem "Nenhum comentário no recorte." quando vazio

**Checkpoint**: Todas as 4 user stories funcionais (US4 já concluída na Phase 3) — feature completa funcionalmente.

---

## Phase 7: User Story 5 - Layout widescreen (Priority: P3)

**Goal**: Layout ocupando a largura total em telas grandes, sem regressão em mobile.

**Independent Test**: Janela ≥1440px mostra conteúdo em largura total; janela mobile empilha sem
overflow horizontal.

### Implementation for User Story 5

- [ ] T019 [US5] Trocar o container raiz de `AvaliacaoCastingPage.tsx` de `mx-auto max-w-3xl` para `w-full px-6 py-6 sm:px-8` (mesmo padrão de `DashboardPage.tsx`/`AgendaPage.tsx`); ajustar o grid 2x2 dos painéis de gráficos (T007–T010) para `grid gap-4 sm:grid-cols-2` de forma que aproveite a largura widescreen

**Checkpoint**: Todas as 5 user stories completas.

---

## Phase 8: Polish & Verificação

**Purpose**: Portões de qualidade da constituição — obrigatórios antes de considerar a feature pronta.

- [ ] T020 [P] Rodar `npx tsc --noEmit` em `frontend/apps/internal`
- [ ] T021 [P] Rodar `npm run build` em `frontend/apps/internal`
- [ ] T022 Criar script `scripts/db/verify_181_avaliacoes.py` (test client Flask, fora de `app.app_context()`, contra `manto_local`) cobrindo: `GET /api/ratings?period=7d` retorna recorte correto; usuário não-SUPERADMIN recebe `show_authors=false`/`is_superadmin=false` e `POST /api/ratings/modo-anonimo` retorna 403; usuário SUPERADMIN alterna `fully_anonymous` e `show_authors` reflete corretamente (inclusive ocultando autoria do próprio SUPERADMIN quando ativado)
- [ ] T023 Rodar o script de verificação e confirmar 100% dos casos passando
- [ ] T024 Checar viewport mobile (375px) via Playwright/browser real — sem overflow horizontal, filtros utilizáveis
- [ ] T025 Checar viewport widescreen (≥1440px) via Playwright/browser real — grid 2x2 lado a lado, largura total aproveitada
- [ ] T026 Atualizar `docs/changelog.html` com entrada da entrega (linguagem simples) e republicar no mesmo link
- [ ] T027 `ruff check app/talents/rating_ops.py` (arquivo Python tocado)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — bloqueia todas as user stories.
- **US4 (Phase 3)**: depende só do Foundational — implementa o "esqueleto" da página (cabeçalho + bloco de privacidade) que as demais phases preenchem.
- **US1 (Phase 4)**: depende do Foundational e do esqueleto criado em US4 (T004) — mesmo arquivo.
- **US2 (Phase 5)**: depende do Foundational; usa os mesmos estados de filtro que US1 já lê (`eventId`, `cat`, `period`, `date_mode`) — sequencial após US1 no mesmo arquivo, mas conceitualmente independente (poderia ser implementada antes de US1 sem quebrar nada).
- **US3 (Phase 6)**: depende do Foundational e de US4 (regra de autoria) — independente de US1/US2 em termos de dado, mas no mesmo arquivo.
- **US5 (Phase 7)**: depende de US1 (grid a ser reorganizado) — última, puramente de layout.
- **Polish (Phase 8)**: depende de todas as stories completas.

### Parallel Opportunities

- T002 (backend) e T003 (tipos TS) são `[P]` — arquivos diferentes.
- T020/T021 (tsc/build) são `[P]` entre si (mesma pasta, comandos independentes, mas não bloqueiam um ao outro).
- Como toda a implementação de UI (US1/US2/US3/US4/US5) converge no mesmo arquivo `AvaliacaoCastingPage.tsx`, essas tasks não são parallelizáveis entre si na prática — a ordem sugerida (US4 → US1 → US2 → US3 → US5) evita retrabalho, mas cada bloco é independentemente verificável via os Acceptance Scenarios do spec.md.

---

## Implementation Strategy

### MVP First

1. Phase 1 (Setup) + Phase 2 (Foundational).
2. Phase 3 (US4 — RBAC) — não-negociável, prioridade máxima de privacidade.
3. Phase 4 (US1 — KPIs/gráficos) — entrega o valor principal da fidelidade visual.
4. **Parar e validar** contra `quickstart.md` antes de seguir.

### Incremental Delivery

5. Phase 5 (US2 — filtros ricos) → validar.
6. Phase 6 (US3 — pontos de atenção/comentários) → validar.
7. Phase 7 (US5 — widescreen) → validar.
8. Phase 8 (Polish/Verificação) → só então considerar a feature pronta para commit/merge.

## Notes

- Todas as tasks de UI tocam o mesmo arquivo (`AvaliacaoCastingPage.tsx`) — implementar na ordem
  das phases evita conflitos de merge dentro da própria sessão de implementação.
- Nenhuma task cria lógica de anonimato no frontend (ver research.md, Decisão 4) — autoria é
  sempre um "passthrough" do campo `author` da API.
- Rodar `ruff check`/`tsc`/build e o script de verificação (Phase 8) antes de qualquer commit,
  por exigência da constituição (Princípio IV, Portões de Qualidade).
