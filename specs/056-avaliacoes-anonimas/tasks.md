---
description: "Task list for feature 056 — Avaliações anônimas + função no evento"
---

# Tasks: Avaliações anônimas + função no evento

**Input**: Design documents from `specs/056-avaliacoes-anonimas/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/anonymity.md, quickstart.md

**Tests**: Não solicitados e o projeto não possui suíte automatizada — verificação manual
via `quickstart.md`.

**Organização**: Tarefas por user story (US1–US4 de `spec.md`), ordem P1 → P1 → P2 → P3.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Confirmar head atual da migration (`flask db current` = `r4a5b6c7d8e9`) para usar
      como `down_revision` da nova migration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Flag global + migration — base do modo total e da regra de exibição.

**⚠️ CRITICAL**: US1/US2 dependem desta fase.

- [X] T002 Adicionar `ratings_fully_anonymous` (Boolean, `nullable=False`,
      `server_default="0"`) em `SiteSetting`, em `app/models.py` (data-model.md)
- [X] T003 Escrever migration manual
      `migrations/versions/<rev>_ratings_fully_anonymous.py` com `add_column`
      (`server_default="0"`), `down_revision = r4a5b6c7d8e9`
- [X] T004 Aplicar a migration (`python -m flask db upgrade`) e confirmar a coluna em
      `instance/manto.db`

**Checkpoint**: Flag global existe e nasce desligado.

---

## Phase 3: User Story 1 - Comentários anônimos por padrão; só super admin vê o autor (Priority: P1) 🎯 MVP

**Goal**: Autores aparecem como "Anônimo" para todos, menos super admin (com modo total
desligado).

**Independent Test**: Página vista por casting → tudo "Anônimo"; por super admin → nomes
reais.

### Implementation for User Story 1

- [X] T005 [US1] Em `app/talents/routes.py` (rota `avaliacoes`), calcular
      `is_superadmin` e `show_authors = is_superadmin and not settings.ratings_fully_anonymous`;
      carregar `settings = SiteSetting.query.get(1)` (research.md item 1)
- [X] T006 [US1] Em `app/talents/routes.py`, alterar `_comment_item` para anonimizar quando
      `show_authors` for falso: `author = "Anônimo"` e nenhum dado identificável (sem nome,
      sem função, sem link) — anonimização no servidor (FR-006)
- [X] T007 [US1] Em `app/talents/routes.py`, passar `show_authors`, `fully_anonymous` e
      `is_superadmin` ao `render_template` de `talents/avaliacoes.html`
- [X] T008 [US1] Em `app/templates/talents/avaliacoes.html`, garantir que onde se exibe
      `author` não haja link de perfil/identificador quando anônimo (apenas o texto
      "Anônimo")

**Checkpoint**: Não-super-admin vê só "Anônimo"; super admin vê nomes (modo total off).

---

## Phase 4: User Story 2 - Botão de modo anônimo total (Priority: P1)

**Goal**: Super admin liga/desliga o modo total (global, persistente); quando ligado, nem
super admin vê o autor.

**Independent Test**: Super admin ativa → tudo "Anônimo" inclusive p/ ele; desativa →
nomes voltam.

### Implementation for User Story 2

- [X] T009 [US2] Em `app/talents/routes.py`, criar a rota
      `POST /talents/avaliacoes/modo-anonimo`: exige super admin (senão 403/flash), seta
      `settings.ratings_fully_anonymous = (request.form.get("enabled") == "1")`, commita,
      flash de sucesso, redirect para a página (contracts/anonymity.md B)
- [X] T010 [US2] Em `app/talents/routes.py`, registrar a alteração em `AuditLog`
      (entity_type="site_setting", action on/off, autor) — FR-010 (research.md item 4)
- [X] T011 [US2] Em `app/templates/talents/avaliacoes.html`, adicionar o botão/controle de
      modo anônimo total **somente para super admin** (`is_superadmin`), refletindo o estado
      `fully_anonymous`, com confirmação e botão que desabilita ao enviar (Princípio V)

**Checkpoint**: Modo total funciona, é global/persistente e só super admin controla.

---

## Phase 5: User Story 3 - Aviso de anonimato no portal (Priority: P2)

**Goal**: Talento vê que a avaliação é anônima ao avaliar pelo portal.

**Independent Test**: Abrir telas de avaliar no portal → aviso de anonimato presente.

### Implementation for User Story 3

- [X] T012 [P] [US3] Em `app/templates/portal/rate.html`, adicionar um aviso claro (pt-BR)
      de que as avaliações são anônimas, no padrão visual de alerta existente (FR-007)
- [X] T013 [P] [US3] Em `app/templates/portal/rate_detail.html`, adicionar o mesmo aviso de
      anonimato (FR-007)

**Checkpoint**: Aviso presente nas telas de avaliação do portal.

---

## Phase 6: User Story 4 - Função no evento ao lado do nome (Priority: P3)

**Goal**: Quando a autoria está visível, exibir a função do autor no evento ao lado do nome.

**Independent Test**: Super admin (modo off) vê a função ao lado do nome; anônimo não mostra
função.

### Implementation for User Story 4

- [X] T014 [US4] Em `app/talents/routes.py`, montar um mapa
      `{(event_id, talent_id): "função"}` com **uma** query a `EventRole` para os pares dos
      comentários exibidos, usando `strip_role_prefix` no `character_name`; múltiplas funções
      unidas por vírgula (research.md item 5, FR-008/FR-009)
- [X] T015 [US4] Em `app/talents/routes.py`, em `_comment_item`, preencher `funcao` somente
      quando `show_authors` (anônimo nunca recebe função — FR-006/FR-008)
- [X] T016 [US4] Em `app/templates/talents/avaliacoes.html`, exibir a função ao lado do nome
      do autor quando houver (comentários e pontos de atenção)

**Checkpoint**: Função aparece ao lado do nome quando visível; ausente quando anônimo.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T017 Executar `ruff check` nos arquivos tocados (`app/models.py`,
      `app/talents/routes.py`); corrigir o que for novo desta feature
- [X] T018 Executar o `quickstart.md` (passos 1–5) no app real: anonimato por perfil, modo
      total, função no evento, aviso no portal, não-regressão de números e auditoria

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: confirmação do head.
- **Foundational (Phase 2)**: BLOQUEIA US2 (flag) e habilita a regra `show_authors` de US1.
- **US1 (Phase 3, P1)**: depende do Foundational (lê o flag). MVP.
- **US2 (Phase 4, P1)**: depende do Foundational e de US1 (mecanismo de exibição).
- **US3 (Phase 5, P2)**: independente (só portal) — pode ir em paralelo.
- **US4 (Phase 6, P3)**: depende de US1 (só exibe função quando autoria visível).
- **Polish (Phase 7)**: depende de tudo anterior.

### Parallel Opportunities

- T012 e T013 (portal, arquivos diferentes) são `[P]` entre si e independentes de US1/US2.
- Tarefas em `app/talents/routes.py` (T005–T007, T009–T010, T014–T015) e em
  `avaliacoes.html` (T008, T011, T016) não são paralelas dentro do mesmo arquivo.

---

## Implementation Strategy

### MVP (US1 + US2)

1. Foundational (flag + migration).
2. US1 (anonimato por padrão; super admin vê).
3. US2 (botão de modo total).
4. **PARAR E VALIDAR**: quickstart passos 1–3.

### Incremental

1. Foundational → base.
2. US1 + US2 → MVP (privacidade), validar quickstart 1–3.
3. US3 → aviso no portal, validar passo 4.
4. US4 → função no evento, validar passo 2.
5. Polish → ruff + quickstart completo.

---

## Notes

- Migration manual (autogenerate quebrado por drift — memória do projeto).
- Anonimização **no servidor**: nome/função nunca entram no HTML quando anônimo (FR-006).
- Comitar a feature como um commit atômico após validação (Princípio IV).
