---
description: "Task list for feature implementation"
---

# Tasks: Reestruturação do Módulo de Talentos (Listagem, Filtros e Perfil)

**Input**: Design documents from `specs/180-talentos-modulo-completo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: incluídos — o usuário pediu explicitamente verificação funcional (backend) e Playwright
(e2e) como parte da entrega, então cada user story carrega sua própria tarefa de teste.

**Organization**: tarefas agrupadas por user story (US1 = P1 filtros, US2 = P2 perfil leitura,
US3 = P3 modo edição), cada uma independentemente testável.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: US1 | US2 | US3 — mapeia para as user stories do spec.md

---

## Phase 1: Setup (Playwright — infraestrutura compartilhada)

**Purpose**: Introduzir Playwright do zero (não existe no monorepo hoje), compartilhado por todas
as user stories que têm spec e2e.

- [X] T001 [P] Adicionar `@playwright/test` como devDependency em `frontend/apps/internal/package.json` e instalar browsers (`npx playwright install --with-deps chromium`)
- [X] T002 [P] Criar `frontend/apps/internal/playwright.config.ts` (webServer → `npm run dev`, `reuseExistingServer: true`, `baseURL` local)
- [X] T003 Criar `frontend/apps/internal/e2e/global-setup.ts` — login via `POST /api/auth/login` com usuário de teste, salva `storageState` para reuso entre specs
- [X] T004 [P] Criar esqueleto de `scripts/db/verify_180_talentos.py` (Flask test client contra `manto_local`, requests fora de `app_context`, sem asserts ainda — cada user story adiciona os seus)

**Checkpoint**: tooling de teste pronto para uso nas fases seguintes.

---

## Phase 2: Foundational (bloqueia US2 e US3 — página de perfil unificada)

**Purpose**: Base da unificação leitura/edição na mesma rota `/talents/:id`, usada tanto por US2
(perfil leitura) quanto por US3 (modo edição). **Não bloqueia US1** (listagem/filtros vive em
arquivos totalmente separados e pode avançar em paralelo).

- [X] T005 Transformar a rota `/talents/:id/edit` em redirect (`<Navigate to="/talents/:id?edit=1" replace />`) em `frontend/apps/internal/src/App.tsx`
- [X] T006 Adicionar estado de modo (`"read" | "edit"` via `useSearchParams` no parâmetro `edit`) ao esqueleto de `frontend/apps/internal/src/pages/TalentDetailPage.tsx`, sem ainda migrar conteúdo
- [X] T007 [P] Estender `FileUpload` com props `existingUrl`, `existingLabel`, `onRemoveExisting` em `frontend/packages/ui/src/components/file-upload.tsx`

**Checkpoint**: fundação pronta — US1 pode já estar em andamento em paralelo; US2 e US3 podem começar.

---

## Phase 3: User Story 1 - Encontrar talentos rapidamente com filtros avançados (Priority: P1) 🎯 MVP

**Goal**: Painel de filtros avançados rico (dropdowns por categoria, aplicação em lote via
"Filtrar"), grid de 5-6 colunas, "já trabalhou" movido para dentro do painel.

**Independent Test**: acessar `/talents`, combinar 3+ filtros de categorias diferentes no painel,
clicar "Filtrar" e confirmar que o resultado atende a todos simultaneamente (E entre categorias,
OU dentro da mesma categoria) — sem depender de nenhuma mudança na tela de perfil.

### Implementation for User Story 1

- [X] T008 [US1] Extrair a query de `character_suggestions()` (`app/talents/routes.py`) para `suggest_characters(q: str) -> list[dict]` em `app/talents/talent_ops.py`; atualizar a rota Jinja para só delegar (mesmo comportamento, zero mudança de resposta)
- [X] T009 [US1] Adicionar suporte a `height_op="eq"` em `search_talents()` — `app/talents/talent_ops.py` (mesmo arquivo de T008, sequencial)
- [X] T010 [US1] Criar `GET /api/talents/character-suggestions` delegando a `suggest_characters()` — `app/api/talents_read.py` (depende de T008)
- [X] T011 [P] [US1] Criar componente compartilhado `FilterDropdown` + `CheckboxList` (popover, busca interna opcional, fecha fora/Esc, Framer Motion) em `frontend/packages/ui/src/components/filter-dropdown.tsx`
- [X] T012 [US1] Criar `frontend/apps/internal/src/components/TalentFilterPanel.tsx` — estado pendente vs. aplicado, 8 categorias (Personagem com busca+sugestão, Idioma, Raça fixa de 5 opções, Tamanho com 2 subseções cima/baixo, Calçado, Altura com operador ≥/≤/=, Passaporte, Tags com busca interna, "Já trabalhou com a Manto"), botão "Filtrar" roxo (depende de T011)
- [X] T013 [US1] Atualizar `TalentDirectoryParams`/`buildDirectoryQuery` em `frontend/apps/internal/src/lib/talents.ts` para aceitar `height_op: "gte"|"lte"|"eq"`
- [X] T014 [US1] Reescrever `frontend/apps/internal/src/pages/TalentsListPage.tsx` para usar `TalentFilterPanel`, remover o checkbox "já trabalhou" da barra principal e os `MultiChoice` antigos (depende de T012, T013)
- [X] T015 [US1] Ajustar breakpoints do grid em `frontend/apps/internal/src/components/TalentMosaic.tsx` para garantir 5-6 colunas em telas widescreen e confirmar formato do badge de medidas (`184cm • XGG • Calçado 45`)
- [X] T016 [P] [US1] Adicionar casos de verificação funcional (altura `eq`, combinação de filtros, personagem, tags) em `scripts/db/verify_180_talentos.py`
- [X] T017 [P] [US1] Criar `frontend/apps/internal/e2e/talents-list.spec.ts` — login, aplicar filtros combinados via painel, confirmar resultado e contagem de colunas do grid (depende de T001-T004, T014)

**Checkpoint**: User Story 1 completa e testável isoladamente (independe de US2/US3).

---

## Phase 4: User Story 2 - Consultar o perfil completo em modo leitura limpo (Priority: P2)

**Goal**: `/talents/:id` em modo leitura sem nenhum controle de edição, com layout em 2 colunas,
KPIs de histórico, filtro de período, e a nova seção "Avaliações e Notas".

**Independent Test**: abrir o perfil de qualquer talento com um usuário sem permissão de edição
(ou sem clicar em "Editar") e confirmar ausência total de controles de upload/edição, presença
dos 4 KPIs, tabela de histórico e seção de avaliações — sem depender do modo de edição (US3)
existir de fato.

### Implementation for User Story 2

- [X] T018 [P] [US2] Adicionar bloco `last_event` (derivado de `history[0]`) ao retorno de `get_talent_profile()` — `app/talents/talent_ops.py`
- [X] T019 [P] [US2] Criar `get_talent_ratings_overview(talent, *, viewer_is_superadmin)` em `app/talents/rating_ops.py` (blocos `received`/`given`, reaproveitando a regra `show_authors`/`fully_anonymous` já existente)
- [X] T020 [US2] Criar `GET /api/talents/<id>/ratings` em `app/api/talents_read.py` delegando a `get_talent_ratings_overview()` (depende de T019)
- [X] T021 [US2] Adicionar `last_event` a `TalentDetail["history"]`, criar `TalentRatingsOverview` types + `useTalentRatings(id)` em `frontend/apps/internal/src/lib/talents.ts` (depende de T018, T020)
- [X] T022 [US2] Reconstruir o modo leitura de `frontend/apps/internal/src/pages/TalentDetailPage.tsx`: layout 2 colunas (coluna esquerda: foto hero, documento com foto, histórico com 4 KPIs + filtro de período + tabela, seção "Avaliações e Notas"; coluna direita: anotações internas read-only, contato, documentos/PIX, aparência com passaporte traduzido e badges de habilidades/tags, veículo com condição corrigida incluindo `cnh_expiration`), painel de aprovação/rejeição quando `status === "pending"`, cabeçalho com link de retorno + botão "Editar" (visível só se `can_edit`, aponta para `?edit=1`) (depende de T006, T021) — implementado junto com o branch de edição completo (T026/T027) no mesmo arquivo, ver notas da Fase 5
- [X] T023 [P] [US2] Adicionar casos de verificação funcional (`last_event`, `/ratings` com e sem modo anônimo) em `scripts/db/verify_180_talentos.py`
- [X] T024 [P] [US2] Criar `frontend/apps/internal/e2e/talents-detail.spec.ts` (parte 1 — leitura): abrir perfil, confirmar zero controles de edição, KPIs, seção de avaliações, painel de pendente quando aplicável (depende de T022)

**Checkpoint**: User Story 2 completa e testável isoladamente, mesmo sem o modo de edição (US3) implementado.

---

## Phase 5: User Story 3 - Editar cadastro em modo dedicado, sem risco de alteração acidental (Priority: P3)

**Goal**: alternador "Editar" na mesma tela revela campos fechados, uploads e permite salvar,
retornando ao modo leitura.

**Independent Test**: com um usuário CASTING/SUPERADMIN, abrir um perfil, confirmar modo leitura
por padrão, clicar "Editar", alterar um campo fechado (ex. tamanho) e uma foto, salvar, e
confirmar retorno ao modo leitura com os novos valores.

### Implementation for User Story 3

- [X] T025 [US3] Remover `frontend/apps/internal/src/pages/TalentEditPage.tsx` e a referência de rota dedicada em `frontend/apps/internal/src/App.tsx` (mantendo só o redirect criado em T005)
- [X] T026 [US3] Adicionar o branch de modo edição a `frontend/apps/internal/src/pages/TalentDetailPage.tsx`: campos fechados (select tamanho superior/inferior/calçado, passaporte), CPF bloqueado para não-superadmin, textarea+select de anotações internas editável, campos de foto/documento via `FileUpload` estendido (T007), migrando estado/validação/`fieldErrors` de `TalentEditPage` (depende de T007, T022, T025) — implementado junto com T022 no mesmo arquivo
- [X] T027 [US3] Ligar o botão "Editar" do cabeçalho à troca de modo e implementar retorno automático ao modo leitura após salvar com sucesso (depende de T026)
- [X] T028 [P] [US3] Adicionar caso de verificação funcional de regressão (`PATCH /api/talents/<id>` continua funcionando, CPF restrito a superadmin) em `scripts/db/verify_180_talentos.py`
- [X] T029 [P] [US3] Completar `frontend/apps/internal/e2e/talents-detail.spec.ts` (parte 2 — edição): alternar leitura→edição, editar campo fechado, salvar, confirmar retorno ao modo leitura, confirmar `/talents/:id/edit` redireciona (sem endpoint de criação de talento para staff — edita e restaura um campo de um talento real em vez de criar/remover, ver research.md §8) (depende de T026, T027)

**Checkpoint**: as 3 user stories funcionam de forma independente e em conjunto.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T030 [P] `npx tsc --noEmit` em `frontend/apps/internal` — 0 erros
- [X] T031 [P] `npm run build` em `frontend/apps/internal` — build OK (warning de chunk >500kB pré-existente, não introduzido por esta feature)
- [~] T032 Rodar `scripts/db/verify_180_talentos.py` contra `manto_local` (todos os casos acumulados de T016/T023/T028) — NÃO EXECUTADO neste ambiente (sem PostgreSQL/manto_local disponível no sandbox); validado apenas `py_compile` + import sanity check (app factory + blueprints carregam, `suggest_characters`/`get_talent_ratings_overview` presentes). **Usuário deve rodar antes do merge.**
- [~] T033 Rodar `npx playwright test` (`talents-list.spec.ts` + `talents-detail.spec.ts`) contra `manto_local` — NÃO EXECUTADO neste ambiente (sem backend/manto_local rodando). **Usuário deve rodar antes do merge.**
- [X] T034 [P] `ruff check` nos arquivos Python tocados — limpo em todos, exceto 4 avisos pré-existentes em `app/talents/routes.py` fora das linhas tocadas (imports não ordenados, variável ambígua `l`, import múltiplo) — não corrigidos por instrução do CLAUDE.md ("legado segue o estilo circundante — não reformatar arquivo inteiro")
- [X] T035 Atualizar `docs/changelog.html` com a entrega do módulo de Talentos reestruturado e republicar no link existente
- [~] T036 Executar o roteiro manual de `quickstart.md` no app real, incluindo viewport widescreen (≥1440px) — PARCIAL: o dev server (`npm run dev:internal`) sobe limpo, sem erros no log; a checagem visual completa não foi possível neste ambiente (navegação do browser de preview bloqueada por política para a porta dinâmica). **Usuário deve conferir visualmente antes do merge.**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: bloqueia US2 e US3; **não bloqueia US1**
- **US1 (Phase 3)**: depende só do Setup (Playwright) para sua tarefa de e2e (T017) — pode avançar em paralelo com a Fase 2
- **US2 (Phase 4)**: depende da Fase 2 completa
- **US3 (Phase 5)**: depende da Fase 2 completa e de T022 (US2) — reaproveita o esqueleto de leitura montado em US2
- **Polish (Phase 6)**: depende de US1 + US2 + US3 completas

### Parallel Opportunities

- T001-T004 (Setup) todas em paralelo
- T007 (Foundational) em paralelo com T005-T006
- Toda a Fase 3 (US1) pode rodar em paralelo com a Fase 2 + Fase 4 (times/streams diferentes), já que não compartilham arquivo
- Dentro de US1: T011 em paralelo com T008-T010 (arquivos diferentes: componente React vs. backend Python)
- Dentro de US2: T018 e T019 em paralelo (arquivos diferentes)
- T016, T023, T028 (casos de verificação funcional) podem ser escritos em paralelo às respectivas implementações, já que só adicionam ao mesmo script em seções distintas

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Fase 1 (Setup)
2. Completar Fase 3 (US1) — já entrega valor real (filtros ricos) mesmo sem tocar no perfil
3. **PARAR e VALIDAR**: rodar T017 isoladamente, confirmar filtros funcionando

### Incremental Delivery

1. Setup → Foundational → US1 pronta (MVP de filtros)
2. US2 pronta → perfil leitura completo, sem risco de clique acidental em upload
3. US3 pronta → edição unificada, `TalentEditPage` removida
4. Fase 6 → validação completa (tsc, build, backend, Playwright, changelog) antes do commit final

---

## Notes

- [P] = arquivos diferentes, sem dependência pendente
- Cada user story é independentemente completável e testável, conforme os Independent Tests do spec.md
- Nenhum template/rota Jinja é editado além da extração de paridade em T008 (mesmo comportamento, mesma resposta)
- Nenhuma migration de banco é necessária (ver data-model.md)
