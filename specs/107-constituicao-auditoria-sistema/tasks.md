# Tasks: Constituição Robusta + Auditoria Geral do Sistema

**Input**: Design documents from `/specs/107-constituicao-auditoria-sistema/`

**Prerequisites**: plan.md, spec.md, research.md (varreduras R1–R5), quickstart.md

**Tests**: verificação via script de varredura + test client contra `manto_local`
(quickstart). Sem migration.

**Organization**: US1 (constituição) independente; US2 (auditoria/relatório) alimenta US3
(correções); correções mecânicas de varredura já mapeadas podem começar junto.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Governança em `.specify/memory/` e `CLAUDE.md`; código em `app/`; relatório em
`specs/107-constituicao-auditoria-sistema/auditoria.md`.

---

## Phase 1: Setup

- [ ] T001 Confirmar app contra a cópia local (`.\scripts\db\run-local.ps1` disponível; `manto_local` no head `a3b4c5d6e7f8`)

---

## Phase 2: Foundational

*(vazio — sem pré-requisito compartilhado)*

---

## Phase 3: User Story 1 - Constituição que reflete a prática real (Priority: P1) 🎯 MVP

**Goal**: constituição v1.3.0 com portões executáveis + princípios das lições 088–106;
CLAUDE.md coerente.

**Independent Test**: roteiro US1 do [quickstart.md](./quickstart.md) — executar cada portão.

### Implementation for User Story 1

- [ ] T002 [US1] Reescrever portões e regras em `.specify/memory/constitution.md` conforme R1 do [research.md](./research.md): portão de verificação funcional automatizada contra `manto_local` (test client, requests fora de app_context) substitui pytest; ruff check obrigatório nos arquivos tocados; ruff format para arquivos novos (legado mantém estilo circundante); mypy recomendado até existir no ambiente; princípio VIII mobile-first para superfícies públicas; Stack/Restrições ganham "migrations sempre manuais" e "verificação contra manto_local, nunca SQLite"; changelog v1.3.0 datado
- [ ] T003 [US1] Alinhar `CLAUDE.md`: seção de comandos/checklist "antes de dizer pronto" coerente com os portões novos (sem citar pytest/tests/ como obrigatório; manter referência ao script de verificação por feature); remover contradições
- [ ] T004 [US1] Verificar US1: executar cada comando citado nos portões no ambiente real; conferir changelog/versão

**Checkpoint**: governança executável — MVP

---

## Phase 4: User Story 2 - Auditoria sistemática com achados priorizados (Priority: P1)

**Goal**: `auditoria.md` cobrindo 12 módulos com achados classificados + backlog priorizado.

**Independent Test**: roteiro US2 do [quickstart.md](./quickstart.md).

### Implementation for User Story 2

- [ ] T005 [US2] Completar a auditoria dirigida por módulo (agenda/eventos, talentos, financeiro, vendas, admin, figurino, ferramentas/orçamento, clientes, revisão, portal, cadastro, auth): para cada um, inspecionar rotas+templates principais nas dimensões da spec (UX, consistência, robustez, forms lentos sem proteção, destrutivas sem confirmação, moeda) — partindo das varreduras já feitas (R2); anotar achados
- [ ] T006 [US2] Escrever `specs/107-constituicao-auditoria-sistema/auditoria.md` no formato R3: resumo executivo (contagens por severidade/status), tabela por módulo, seção "Backlog priorizado" (incluindo R5: innerHTML/XSS, pytest+mypy, cores hardcoded, utcnow, otimizações)
- [ ] T007 [US2] Referenciar o relatório na memória do projeto (MEMORY.md → apontador para auditoria.md e backlog)

**Checkpoint**: mapa completo — correções da US3 rastreáveis ao relatório

---

## Phase 5: User Story 3 - Correções de alto impacto aplicadas (Priority: P2)

**Goal**: zerar as classes objetivas: moeda BR, except sem log, print, duplo envio nos
fluxos principais, alert() de erro, destrutivas sem confirmação.

**Independent Test**: varreduras do quickstart retornam zero + telas tocadas renderizam.

### Implementation for User Story 3

- [ ] T008 [P] [US3] Moeda → `| brl`: `app/templates/home.html` (KPI linha ~567), `app/templates/talent_detail.html` (linhas ~386/437), `app/templates/desempenho.html` (linhas ~27/61), `app/templates/event_create.html` (5 ocorrências linhas ~243–273), `app/templates/financeiro/dashboard.html` (corpo do macro `money(v)` → `R$ {{ (v or 0) | brl }}`)
- [ ] T009 [P] [US3] Logging nos except silenciosos (padrão R4): `app/calendar/routes.py` (1956, 2021), `app/calendar/service.py` (186), `app/cli.py` (71), `app/email_service.py` (500), `app/models.py` (365), `app/storage.py` (201), `app/talents/importer.py` (34, 42) — conferir também `app/figurino/routes.py:368`; e `app/figurino/drive_service.py:91` print → logger
- [ ] T010 [US3] Duplo envio: proteger os forms de ação lenta dos fluxos principais identificados na T005 (mínimo: criação/edição de evento, forms do financeiro/orçamento e admin sem proteção) com o padrão do projeto (botão desabilita + estado); listar na auditoria quais foram protegidos
- [ ] T011 [US3] alert() de erro → feedback inline nas telas identificadas (event_detail, figurino_form, financeiro/pagamentos, orcamento/resultado, orcamento/settings — analisar caso a caso; confirm() de confirmação permanece); destrutivas sem confirmação encontradas na T005 ganham confirm
- [ ] T012 [US3] Atualizar status dos achados corrigidos em `auditoria.md` (📋 → ✅)
- [ ] T013 [US3] Verificação US3: script de varredura (zero `{:,` em templates, zero except silencioso nos pontos tocados, zero print de debug) + renderização das telas tocadas via test client contra `manto_local` (requests fora de app_context)

**Checkpoint**: violações objetivas zeradas, rastreadas no relatório

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T014 `ruff check` nos arquivos Python tocados; textos pt-BR; re-execução rápida do quickstart completo
- [ ] T015 Commits atômicos por story + merge da branch `107-constituicao-auditoria-sistema` em `main` + push (stage explícito)

---

## Dependencies & Execution Order

- **US1 (Phase 3)**: independente — pode ser o primeiro commit
- **US2 (Phase 4)**: T005 → T006 → T007; varreduras mecânicas já existem (R2), então T008/T009 [P] podem começar em paralelo a T005
- **US3 (Phase 5)**: T008/T009 paralelos entre si; T010/T011 dependem de T005 (lista final); T012 depende de tudo; T013 fecha
- **Polish**: depende de tudo

### Parallel Opportunities

- T008 (templates) ∥ T009 (Python) ∥ T002 (constituição) — arquivos disjuntos

## Implementation Strategy

US1 (governança) → US2 auditoria completa → US3 correções (mecânicas primeiro, depois as
dependentes da lista) → Polish. Um commit por story; varredura + renderização a cada
checkpoint.
