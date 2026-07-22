# Tasks: Leitura e Gestão de Talentos e Figurino (154)

**Input**: `spec.md`, `plan.md`, `data-model.md`, `contracts/talents-figurino-endpoints.md`,
`quickstart.md`
**Tests**: verificação funcional automatizada (`scripts/db/verify_154_talentos_figurino.py`)
contra `manto_local`, por paridade API×Jinja — mesmo padrão de 146-153. Uma tarefa por User
Story estende o mesmo script.

## Phase 1: Setup

- [X] T001 Criar `app/talents/talent_ops.py` e `app/figurino/figurino_ops.py` (módulos vazios
  com docstring explicando o papel — núcleo puro, sem `request`/`flash`/`current_user`, mesmo
  padrão de `casting_ops.py`/`event_ops.py`/`observation_ops.py`).

## Phase 2: Foundational (bloqueia todas as User Stories)

**⚠️ CRÍTICO — nenhuma User Story pode começar antes desta fase.**

- [X] T002 [P] Corrigir `assetUrl` em `frontend/packages/api-client/src/client.ts`: se `path`
  começar com `http://` ou `https://`, devolver sem prefixar `API_BASE` (fotos legadas do
  Drive em talento/figurino); comportamento atual inalterado para paths relativos.
- [X] T003 [P] Criar `app/api/talents_read.py`, `app/api/talents_write.py`,
  `app/api/figurino_read.py`, `app/api/figurino_write.py` (esqueleto: imports, blueprint
  `api_bp` importado, sem rotas ainda) e registrar os 4 no `app/api/__init__.py` (efeito
  colateral de import, mesmo padrão de `agenda`/`agenda_write`).
- [X] T004 [P] Criar `scripts/db/verify_154_talentos_figurino.py` (esqueleto): `create_app()`,
  helpers `check`/`make_user`/`mk_talent`/`mk_figurino_sheet`/`cleanup_all_test_data`
  (defensivo, mesmo padrão da `verify_153`), login via test client, sem asserts de fluxo
  ainda.

**Checkpoint**: módulos/arquivos criados, `assetUrl` corrigido, esqueleto de verificação
pronto. A partir daqui as User Stories são independentes entre si.

---

## Phase 3: User Story 1 — Buscar e consultar talentos (P1) 🎯 MVP

**Goal**: buscar/filtrar/paginar talentos e ver o perfil completo (com histórico de eventos)
pela tela React.

**Independent Test**: abrir a lista, buscar por nome, aplicar um filtro, abrir um perfil e
conferir que os dados batem com os da tela antiga.

### Backend

- [X] T005 [US1] `search_talents(*, status, q, ja_trabalhou, language=None, race=None,
  top=None, bottom=None, shoe=None, height_op=None, height_value=None, passport=None,
  tags=None, character=None, page=1, page_size=60) -> dict` em `app/talents/talent_ops.py` —
  extrai a lógica de filtro/paginação de `list_talents` (mesma query, mesmas opções de
  filtro quando `status=active`) sem duplicar.
- [X] T006 [US1] `get_talent_profile(talent, *, date_from=None, date_to=None) -> dict` em
  `app/talents/talent_ops.py` — extrai a lógica de histórico/totais de `talent_detail` (sem
  os blocos de avaliação, que ficam fora desta fatia).
- [X] T007 [US1] ~~Refatorar `list_talents`/`talent_detail`~~ **N/A** — descoberto durante a
  implementação que o template `talents_list.html` usa métodos do objeto `Pagination` do
  Flask-SQLAlchemy (`iter_pages`, `has_next`/`has_prev`, `next_num`/`prev_num`) que um dict
  simples não replica; `list_talents`/`talent_detail` (GET) ficam INTOCADOS, mesmo padrão já
  usado pela Agenda (145) — ver plan.md Design Decision 2. `search_talents`/
  `get_talent_profile` são consumidos só pela API, verificados por paridade contra o Jinja.
- [X] T008 [US1] `GET /api/talents/directory` e `GET /api/talents/<id>` em
  `app/api/talents_read.py` (leitura aberta — `@api_login_required`, sem gate de papel).
  Depende de T005, T006.

### Frontend

- [X] T009 [P] [US1] Criar `frontend/apps/internal/src/lib/talents.ts` com
  `useTalentDirectory(params)` e `useTalent(id)` (`useQuery`, mesmo padrão de `agenda.ts`).
- [X] T010 [US1] Criar `frontend/apps/internal/src/pages/TalentsListPage.tsx`: abas Ativos/
  Pendentes, busca por nome, painel de filtros, grade de cards (foto/placeholder, nome, alerta,
  meta), paginação. Usa `assetUrl` (T002) para fotos.
- [X] T011 [US1] Criar `frontend/apps/internal/src/pages/TalentDetailPage.tsx`: contato,
  aparência, documentos (fotos/links, sem upload), PIX, veículo, anotação interna (só
  leitura nesta story), histórico de eventos com total de cachê (`formatBRL`).
- [X] T012 [US1] Adicionar rotas `/talents` e `/talents/:id` em `App.tsx` + link de navegação
  (menu lateral, se existir um componente de navegação já usado pelas outras telas React).
  Depende de T010, T011.
- [X] T013 [US1] Estender `scripts/db/verify_154_talentos_figurino.py`: paridade API×Jinja
  para busca (nome + cada filtro), paginação, e perfil (dados + histórico/total de cachê).

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 4: User Story 2 — Aprovar ou rejeitar talento pendente (P2)

**Goal**: aprovar/rejeitar cadastro pendente pela tela React.

**Independent Test**: na aba Pendentes, aprovar um talento (vira ativo) e rejeitar outro
(desaparece).

### Backend

- [X] T014 [US2] `approve_talent_status(talent) -> None` e `reject_talent_record(talent) ->
  bool` em `app/talents/talent_ops.py` — paridade exata com `approve_talent`/`reject_talent`
  (approve sempre aplica; reject só se `status == "pending"`).
- [X] T015 [US2] Refatorar `approve_talent`/`reject_talent` em `app/talents/routes.py` para
  chamar o núcleo (wrapper fino + `flash`). Depende de T014.
- [X] T016 [US2] `POST /api/talents/<id>/approve` e `POST /api/talents/<id>/reject` em
  `app/api/talents_write.py` (gate CASTING/SUPERADMIN). Depende de T014.

### Frontend

- [X] T017 [P] [US2] Em `talents.ts`, adicionar `useApproveTalent`, `useRejectTalent`
  (`useMutation`, invalida `["talents-directory"]` no sucesso).
- [X] T018 [US2] Em `TalentsListPage.tsx`: botões Aprovar/Rejeitar nos cards da aba
  Pendentes, visíveis só quando o usuário pode editar (usar o mesmo `can_edit` do perfil, ou
  expor a flag na resposta de `directory` — decidir durante a implementação, documentar
  se divergir do plan.md); `window.confirm` na rejeição. Depende de T017.
- [X] T019 [US2] Estender `verify_154_talentos_figurino.py`: aprovar (idempotente, sempre
  200), rejeitar (200 se pendente, 400 se não), 403 para não-CASTING/SUPERADMIN.

**Checkpoint**: US2 completa e testável isoladamente, sem dependência de US1 (mas reusa a
lista da US1 na prática).

---

## Phase 5: User Story 3 — Editar cadastro e anotações internas (P3)

**Goal**: editar dados do talento (CPF só SUPERADMIN) e salvar anotação interna.

**Independent Test**: editar um campo do talento e salvar; salvar anotação com nível de
alerta; confirmar que CPF só é alterável por SUPERADMIN.

### Backend

- [X] T020 [US3] `update_talent_fields(talent, data: dict, *, is_superadmin: bool) ->
  dict[str, str]` e `save_notes(talent, *, notes, warning_level) -> None` em
  `app/talents/talent_ops.py` — paridade com `edit_talent`/`save_talent_notes` (CPF: 11
  dígitos + unicidade, só aplicado se `is_superadmin`; mapa de erros no lugar de `flash`).
- [X] T021 [US3] Refatorar `edit_talent`/`save_talent_notes` em `app/talents/routes.py` para
  chamar o núcleo. Depende de T020.
- [X] T022 [US3] `PATCH /api/talents/<id>` e `POST /api/talents/<id>/notes` em
  `app/api/talents_write.py` (gate CASTING/SUPERADMIN). Depende de T020.

### Frontend

- [X] T023 [P] [US3] Em `talents.ts`, adicionar `useUpdateTalent`, `useSaveTalentNotes`.
- [X] T024 [US3] Criar `frontend/apps/internal/src/pages/TalentEditPage.tsx`: form com todos
  os campos editáveis; campo CPF só habilitado quando `is_superadmin` (flag do usuário
  autenticado, mesmo padrão de `data.flags.is_superadmin` na Agenda); erros de campo do 400
  mapeados no form (Princípio V). Depende de T023.
- [X] T025 [US3] Em `TalentDetailPage.tsx`: painel de anotação interna editável (textarea +
  select de nível de alerta) visível só a quem pode editar; link/botão para
  `TalentEditPage`. Depende de T023.
- [X] T026 [US3] Adicionar rota `/talents/:id/edit` em `App.tsx`. Depende de T024.
- [X] T027 [US3] Estender `verify_154_talentos_figurino.py`: editar (campos comuns +
  CPF-só-SUPERADMIN, incl. 400 de CPF inválido/duplicado), salvar anotação, 403 para
  não-CASTING/SUPERADMIN.

**Checkpoint**: US3 completa e testável isoladamente.

---

## Phase 6: User Story 4 — Consultar e gerir fichas de figurino (P4)

**Goal**: listar/criar/editar/excluir ficha de figurino pela tela React (sem foto).

**Independent Test**: listar fichas, criar uma nova com peças, editar as peças de uma
existente, excluir uma ficha.

### Backend

- [X] T028 [US4] `list_sheets() -> dict`, `create_sheet(*, character_name, pieces, notes) ->
  FigurinoSheet | None`, `edit_sheet(sheet, *, character_name, pieces, notes) -> bool`,
  `delete_sheet(sheet) -> None` em `app/figurino/figurino_ops.py` — paridade com
  `figurinos`/`new_sheet`/`edit_sheet`/`delete_sheet` (sem parâmetro de foto; `delete_sheet`
  mantém `delete_file(sheet.photo_filename)` e desvincula `EventRole.figurino_sheet_id`).
- [X] T029 [US4] Refatorar `new_sheet`/`edit_sheet`/`delete_sheet` (POST) em
  `app/figurino/routes.py` para chamar o núcleo (upload de foto continua só no wrapper).
  `figurinos()` (GET) fica INTOCADO, mesmo motivo de T007 (fora do escopo tocar o padrão de
  listagem Jinja). Depende de T028.
- [X] T030 [US4] `GET /api/figurino`, `POST /api/figurino`, `PATCH /api/figurino/<id>`,
  `DELETE /api/figurino/<id>` em `app/api/figurino_read.py`/`figurino_write.py` (leitura
  aberta; escrita FIGURINO/SUPERADMIN). Depende de T028.

### Frontend

- [X] T031 [P] [US4] Criar `frontend/apps/internal/src/lib/figurino.ts` com
  `useFigurinoSheets`, `useCreateFigurinoSheet`, `useEditFigurinoSheet`,
  `useDeleteFigurinoSheet`.
- [X] T032 [US4] Criar `frontend/apps/internal/src/pages/FigurinoListPage.tsx`: grade de
  fichas (foto via `assetUrl`/placeholder, nome, contagem de peças), aviso de "personagens
  sem ficha", busca client-side. Depende de T031.
- [X] T033 [US4] Criar `frontend/apps/internal/src/pages/FigurinoFormPage.tsx`: nome do
  personagem, lista dinâmica de peças (nome+quantidade, adicionar/remover linha), notas; sem
  campo de foto nesta fatia. Depende de T031.
- [X] T034 [US4] Adicionar rotas `/figurinos`, `/figurinos/new`, `/figurinos/:id/edit` em
  `App.tsx`. Depende de T032, T033.
- [X] T035 [US4] Estender `verify_154_talentos_figurino.py`: listar (incl.
  `chars_without_sheet`), criar/editar (incl. 400 nome vazio), excluir (incl. desvincula
  `EventRole.figurino_sheet_id`), 403 para não-FIGURINO/SUPERADMIN.

**Checkpoint**: todas as 4 User Stories completas.

---

## Phase 7: Polish & Cross-Cutting

- [X] T036 Rodar `scripts/db/verify_154_talentos_figurino.py` completo contra `manto_local` e
  corrigir qualquer falha antes de prosseguir.
- [X] T037 [P] `ruff check` nos arquivos Python tocados/novos; `ruff format` nos arquivos
  novos (`talent_ops.py`, `figurino_ops.py`, `talents_read.py`, `talents_write.py`,
  `figurino_read.py`, `figurino_write.py`, `verify_154_talentos_figurino.py`).
  Docstrings/type hints em todas as funções novas.
- [X] T038 [P] `npx tsc --noEmit` e `npm run build` em `frontend/` sem erros.
- [X] T039 Conferir viewport mobile (320–430px) das novas telas (lista de talentos em cards,
  perfil, formulários, catálogo de figurino) — revisão estrutural via Tailwind (sem
  `chromium-cli`/Playwright disponível neste ambiente, mesma limitação da 153).
- [X] T040 Adicionar entrada em `docs/changelog.html` e republicar no link já existente.
- [X] T041 Commit atômico + merge de `154-talentos-figurino-leitura` em `main` (stage
  explícito, nunca `git add -A`), seguido de push — só depois de T036-T040 passarem.

## Dependencies

- **Setup (T001)** → precede a fase Foundational.
- **Foundational (T002-T004)** → bloqueia TODAS as User Stories (T005 em diante).
- **US1 (T005-T013)**, **US2 (T014-T019)**, **US3 (T020-T027)**, **US4 (T028-T035)** → cada
  uma independente das outras após a Foundational (US2/US3 tocam os mesmos arquivos de US1 —
  `talent_ops.py`/`talents_read.py`ou `write`/`routes.py` — então não rodam em paralelo real
  entre si, mas não há dependência lógica).
- **Polish (T036-T041)** → depende de todas as User Stories implementadas nesta execução.

## Implementation Strategy

**MVP = User Story 1** (buscar/consultar talentos): maior valor imediato — é a ação mais
frequente do Casting no dia a dia. US2-US4 entregam valor incremental, qualquer uma pode parar
aqui sem quebrar as anteriores.
