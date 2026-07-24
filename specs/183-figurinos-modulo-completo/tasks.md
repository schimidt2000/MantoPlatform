---

description: "Task list template for feature implementation"
---

# Tasks: Reestruturação do Banco de Figurinos

**Input**: Design documents from `/specs/183-figurinos-modulo-completo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-figurino.md, quickstart.md

**Tests**: Verificação funcional automatizada (script contra `manto_local`) e Playwright são
exigidos pela constituição do projeto (Portões de Qualidade) — incluídos como tarefas próprias,
não apenas "se pedido".

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir implementação e teste
independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: A qual user story a tarefa pertence (US1..US4)
- Caminhos de arquivo exatos em cada descrição

## Path Conventions (Web app — backend Flask + frontend React)

- Backend: `app/models.py`, `app/figurino/figurino_ops.py`, `app/api/figurino_write.py`,
  `migrations/versions/`
- Frontend: `frontend/apps/internal/src/lib/figurino.ts`,
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx`,
  `frontend/apps/internal/src/pages/FigurinoFormPage.tsx`,
  `frontend/apps/internal/e2e/figurinos.spec.ts`
- Verificação: `scripts/db/verify_183_figurinos_modulo_completo.py`

---

## Phase 1: Setup

**Purpose**: Confirmar ambiente pronto antes de tocar código.

- [X] T001 Atualizar/confirmar `manto_local` no head das migrations (`python -m flask db heads`
  com `DATABASE_URL` apontando para `manto_local`, via `.\scripts\db\run-local.ps1`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhum pré-requisito bloqueante compartilhado além do Setup — cada user story carrega
seu próprio modelo/migration/endpoint, isolados por schema (US3 usa uma tabela nova, US4 usa uma
coluna nova; nenhuma delas depende da outra). US1 e US2 são puramente frontend sobre a API já
existente hoje.

**Checkpoint**: Nenhuma tarefa nesta fase — prosseguir direto para a Phase 3.

---

## Phase 3: User Story 1 - Grade densa e enquadramento de fotos (Priority: P1) 🎯 MVP

**Goal**: `/figurinos` exibe uma grade de 5-6 colunas em widescreen, cards com foto em quadro
vertical (`aspect-[3/4]`, `object-cover object-top`) mostrando o figurino inteiro, e rodapé com
nome/quantidade de peças/data.

**Independent Test**: Abrir `/figurinos` com fichas cadastradas (com e sem foto) e conferir grade,
enquadramento e rodapé — não depende de nenhuma outra user story ou de mudança de backend.

### Implementation for User Story 1

- [X] T002 [US1] Reescrever o wrapper da grade em
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx` para
  `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3`
- [X] T003 [US1] Reescrever o card em `frontend/apps/internal/src/pages/FigurinoListPage.tsx`:
  quadro de foto `aspect-[3/4] w-full overflow-hidden rounded-md bg-surface-2`, `<img>` com
  `object-cover object-top h-full w-full`, placeholder (📷) ocupando o mesmo quadro quando
  `photo_url` for nulo
- [X] T004 [US1] Adicionar rodapé do card em
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx`: nome do personagem, `{n} peça(s)`,
  data de edição (`updated_at` → fallback `created_at` → `"—"`, formatada em pt-BR)
- [X] T005 [US1] Verificar em preview: desktop widescreen (5-6 colunas), breakpoints menores
  (degradação sem quebra), card sem foto mantendo o grid alinhado — itens 1-4 de `quickstart.md`

**Checkpoint**: Grade e enquadramento funcionais e testáveis isoladamente (MVP visual).

---

## Phase 4: User Story 2 - Ações do card: Imprimir e Editar (Priority: P1)

**Goal**: Cada card tem um botão primário "Imprimir" (abre a ficha de impressão legada em nova
aba) e um ícone de lápis "Editar" (visível só para FIGURINO/SUPERADMIN).

**Independent Test**: Em um card, clicar "Imprimir" abre `/figurinos/<id>/print` em nova aba;
clicar no lápis leva à edição — testável isoladamente sobre a grade da US1, sem mudança de
backend.

### Implementation for User Story 2

- [X] T006 [US2] Adicionar botão primário "Imprimir" no card em
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx` que chama
  `window.open(\`/figurinos/${sheet.id}/print\`, "_blank")`
- [X] T007 [US2] Adicionar ícone/botão "Editar" (lápis) no card em
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx`, linkando para
  `/figurinos/${sheet.id}/edit`, visível apenas quando `canEdit` (FIGURINO/SUPERADMIN)
- [X] T008 [US2] Verificar: "Imprimir" abre a rota Jinja legada existente sem alterar
  `app/figurino/routes.py`/`app/templates/figurino_print.html`; usuário sem permissão de edição
  não vê o ícone de lápis — itens 5-6 de `quickstart.md`

**Checkpoint**: US1 + US2 juntas entregam a grade completa com ações por card.

---

## Phase 5: User Story 3 - Painel "Figurinos Faltantes" com RBAC e ações (Priority: P2)

**Goal**: Painel colapsável (fechado por padrão) visível só para SUPERADMIN, com contagem no
título, ação de descartar um alerta e ação de associar o personagem a uma ficha existente
(atualizando os cargos de evento).

**Independent Test**: Logar como SUPERADMIN, abrir o painel, descartar um item, associar outro a
uma ficha; logar como não-SUPERADMIN e confirmar que o painel não aparece — testável isoladamente
(não depende de US1/US2 para funcionar, ainda que visualmente componha a mesma tela).

### Backend for User Story 3

- [X] T009 [US3] Adicionar modelo `FigurinoMissingDismissal` em `app/models.py` (`id`,
  `character_name_norm` indexado, `event_role_ids` Text/JSON, `dismissed_at`,
  `dismissed_by` FK `users.id`) — ver `data-model.md`
- [X] T010 [US3] Criar migration manual em `migrations/versions/` para a tabela
  `figurino_missing_dismissals` (upgrade/downgrade completos, `down_revision` = head atual)
- [X] T011 [US3] Reescrever `list_sheets()` em `app/figurino/figurino_ops.py`: um cargo de evento
  é "coberto" quando `figurino_sheet_id IS NOT NULL` OU nome normalizado bate com alguma ficha;
  `chars_without_sheet` passa a retornar `[{character_name, character_name_norm}]`, excluindo
  personagens cujos `EventRole.id` pendentes estejam todos contidos em algum descarte vigente
  (ver `research.md` §6-7)
- [X] T012 [US3] Implementar `dismiss_missing_character(character_name_norm, dismissed_by)` em
  `app/figurino/figurino_ops.py`: cria ou mescla o registro `FigurinoMissingDismissal` com os
  `EventRole.id` pendentes atuais daquele nome; retorna `False` se não houver nenhum pendente
- [X] T013 [US3] Implementar `associate_missing_character(character_name_norm, sheet_id)` em
  `app/figurino/figurino_ops.py`: seta `figurino_sheet_id = sheet_id` em todo `EventRole` pendente
  com aquele nome normalizado; retorna a contagem atualizada (`0` se a ficha não existir ou não
  houver pendentes)
- [X] T014 [US3] Adicionar endpoint `POST /api/figurino/faltantes/dispensar` em
  `app/api/figurino_write.py` (RBAC: SUPERADMIN apenas; 403 caso contrário; 400 se nada a
  descartar) — ver `contracts/api-figurino.md`
- [X] T015 [US3] Adicionar endpoint `POST /api/figurino/faltantes/associar` em
  `app/api/figurino_write.py` (RBAC: SUPERADMIN apenas; 404 se ficha não existir; 400 se nada
  pendente) — ver `contracts/api-figurino.md`

### Frontend for User Story 3

- [X] T016 [US3] Atualizar `frontend/apps/internal/src/lib/figurino.ts`: tipo `MissingCharacter`
  (`character_name`, `character_name_norm`), `FigurinoList.chars_without_sheet` como
  `MissingCharacter[]`, hooks `useDismissMissingCharacter()` e
  `useAssociateMissingCharacter()` (invalidando a query `["figurino"]`)
- [X] T017 [US3] Substituir o bloco fixo de faltantes por `SectorPanel`
  (`defaultOpen={false}`, título `` `⚠️ Figurinos solicitados/faltantes (${n} itens)` ``) em
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx`, renderizado apenas quando
  `user?.is_superadmin`
- [X] T018 [US3] Implementar ação "Excluir" por item (confirmação via `window.confirm()`,
  `loading`/`disabled` no botão durante a mutation) dentro do painel em
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx`
- [X] T019 [US3] Implementar ação "Associar a uma ficha existente" por item (select nativo
  populado por `useFigurinoSheets().data.items`, botão "Confirmar" desabilitado até uma ficha ser
  escolhida, `loading` durante a mutation) dentro do painel em
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx`

### Verification for User Story 3

- [X] T020 [US3] Escrever `scripts/db/verify_183_figurinos_modulo_completo.py` (test client Flask,
  requests fora de `app_context`, contra `manto_local`) cobrindo: listar com faltantes, dispensar
  (200 e 400 sem pendente), associar (200, 404 ficha inexistente, 400 sem pendente), 403 para
  usuário sem papel SUPERADMIN nos dois endpoints novos
- [X] T021 [US3] Rodar a verificação funcional contra `manto_local` e confirmar 100% de sucesso

**Checkpoint**: Painel de faltantes funcional, restrito a SUPERADMIN, com ações persistentes.

---

## Phase 6: User Story 4 - Busca por nome e filtro por tags (Priority: P3)

**Goal**: Campo de busca por nome de ficha/personagem e filtro por tag, combináveis por
interseção; fichas ganham um campo de tags editável.

**Independent Test**: Cadastrar fichas com tags, filtrar por uma tag, buscar por nome parcial,
combinar os dois — testável isoladamente (não depende de US1/US2/US3 para funcionar).

### Backend for User Story 4

- [X] T022 [US4] Adicionar coluna `tags` (Text, JSON de `list[str]`, nullable) em
  `FigurinoSheet` (`app/models.py`) + property `tags_list` (paridade com `pieces_list`)
- [X] T023 [US4] Criar migration manual em `migrations/versions/` para a coluna `tags` em
  `figurino_sheets` (upgrade/downgrade completos)
- [X] T024 [US4] Adicionar `_clean_tags()` e aceitar `tags` em `create_sheet`/`edit_sheet` em
  `app/figurino/figurino_ops.py`; incluir `tags` no JSON retornado por `list_sheets()`
- [X] T025 [US4] Aceitar campo opcional `tags: string[]` no body de `POST /api/figurino` e
  `PATCH /api/figurino/<id>` em `app/api/figurino_write.py`

### Frontend for User Story 4

- [X] T026 [US4] Atualizar `frontend/apps/internal/src/lib/figurino.ts`: `tags: string[]` em
  `FigurinoSheetItem` e `FigurinoSheetInput`
- [X] T027 [US4] Adicionar editor de tags (chips: adicionar via Enter/vírgula, remover com ✕) em
  `frontend/apps/internal/src/pages/FigurinoFormPage.tsx`
- [X] T028 [US4] Adicionar campo de busca por nome (client-side, case-insensitive, sem acento) em
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx`
- [X] T029 [US4] Adicionar filtro de tags com `FilterDropdown` + `CheckboxList` (`@manto/ui`),
  opções derivadas da união das tags carregadas, combinando com a busca por interseção, em
  `frontend/apps/internal/src/pages/FigurinoListPage.tsx`

**Checkpoint**: Todas as 4 user stories funcionais de forma independente.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Portões de qualidade da constituição, validação end-to-end e entrega.

- [X] T030 Rodar `npx tsc --noEmit` em `frontend/apps/internal` e corrigir quaisquer erros de tipo
- [X] T031 Rodar `npm run build` (`vite build`) em `frontend/apps/internal` e corrigir quaisquer
  erros
- [X] T032 [P] Escrever `frontend/apps/internal/e2e/figurinos.spec.ts` (Playwright): grade/
  enquadramento, ações do card, painel de faltantes (RBAC + descartar + associar), busca/filtro
- [X] T033 Rodar a suíte Playwright contra `manto_local` e corrigir falhas
- [X] T034 [P] Adicionar entrada em `docs/changelog.html` descrevendo a entrega (linguagem
  simples) e republicar no link já existente
- [ ] T035 Commit atômico final, merge em `main` e push para `origin` (após todos os portões de
  qualidade passarem)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: vazia — nenhuma tarefa bloqueante adicional.
- **US1 (Phase 3)**: depende só do Setup — pode começar imediatamente.
- **US2 (Phase 4)**: depende só do Setup; compõe visualmente sobre US1 mas não depende do código
  dela (mesmo arquivo, seção diferente do card).
- **US3 (Phase 5)**: depende só do Setup — schema (`FigurinoMissingDismissal`) e endpoints são
  isolados de US1/US2/US4.
- **US4 (Phase 6)**: depende só do Setup — schema (`tags`) e endpoints são isolados de
  US1/US2/US3.
- **Polish (Phase 7)**: depende de todas as user stories desejadas estarem completas.

### Within Each User Story

- Modelo/migration → ops → endpoint (backend) antes de tipos/hooks → UI (frontend).
- US3 e US4 tocam os mesmos dois arquivos frontend (`lib/figurino.ts`,
  `FigurinoListPage.tsx`) que US1/US2 — execução sequencial nesses arquivos, ainda que as stories
  sejam logicamente independentes (conflito de arquivo, não de lógica).

### Parallel Opportunities

- T009 (modelo US3) e T022 (coluna US4) tocam o mesmo arquivo `app/models.py` — não marcar `[P]`
  entre si, mas cada um é independente das demais tarefas de sua própria story.
- T032 (Playwright) e T034 (changelog) são `[P]` — arquivos diferentes de T030/T031/T033.
- Migrations (T010, T023) devem ser aplicadas em sequência (mesmo `down_revision` chain), mas
  podem ser *escritas* em paralelo por serem tabelas/colunas independentes — aplicar uma de cada
  vez com `flask db upgrade`.

---

## Parallel Example: User Story 3 vs. User Story 4 (backend)

```bash
# Podem ser desenvolvidas em paralelo por serem schemas independentes:
Task: "Adicionar modelo FigurinoMissingDismissal em app/models.py" (US3, T009)
Task: "Adicionar coluna tags em FigurinoSheet em app/models.py" (US4, T022)
# (mesmo arquivo — na prática, aplicar uma migration por vez e resolver o merge do models.py)
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1 (Setup).
2. Completar Phase 3 (US1) — grade densa e enquadramento.
3. **PARAR e VALIDAR**: conferir a US1 isoladamente no preview.
4. US1 sozinha já resolve a queixa mais visível do módulo (fotos cortadas, grade larga).

### Entrega Incremental

1. Setup → US1 (grade/enquadramento) → validar.
2. + US2 (ações do card) → validar.
3. + US3 (painel de faltantes RBAC) → validar (inclui migration + verificação funcional).
4. + US4 (busca/filtro por tags) → validar (inclui migration).
5. Polish (tsc, build, Playwright, changelog, commit/merge/push).

## Notes

- `[P]` = arquivos diferentes, sem dependência.
- Rótulo `[Story]` mapeia a tarefa a uma user story de `spec.md`.
- Cada user story é independentemente completável e testável, mesmo compartilhando os dois
  arquivos de frontend principais (execução sequencial nesses arquivos, não paralela).
- Commits atômicos por grupo lógico de tarefas (ex.: um commit por user story), seguindo o padrão
  já usado neste repositório (specs commitados separadamente do código).
- Migrations sempre escritas à mão, com upgrade/downgrade completos (Princípio da constituição).
