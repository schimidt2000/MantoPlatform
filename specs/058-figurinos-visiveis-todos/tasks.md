---
description: "Task list for feature 058 — Figurinos visíveis a todos (edição restrita)"
---

# Tasks: Figurinos visíveis a todos (edição restrita)

**Input**: Design documents from `specs/058-figurinos-visiveis-todos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/access.md, quickstart.md

**Tests**: Não solicitados e o projeto não possui suíte automatizada — verificação via test
client + `quickstart.md`.

**Organização**: por user story (US1 visualização, US2 edição restrita). Ordem P1 → P1.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Confirmar que as rotas de figurino hoje têm só `@login_required` (sem guarda de
      papel) e que o link do menu está restrito a FIGURINO/SUPERADMIN, em
      `app/figurino/routes.py` e `app/templates/base.html`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Helper de permissão de edição, base da guarda do servidor.

- [X] T002 Em `app/figurino/routes.py`, adicionar `_can_edit_figurino()` (True se
      `current_user` tem papel SUPERADMIN ou FIGURINO), seguindo o padrão de `_is_superadmin()`;
      importar `abort` do Flask se ainda não importado

**Checkpoint**: Helper disponível para as guardas.

---

## Phase 3: User Story 1 - Consultar figurinos (todos os usuários) (Priority: P1) 🎯 MVP

**Goal**: Qualquer usuário autenticado vê o menu, a lista e a impressão.

**Independent Test**: Logar como comercial, ver "Figurinos" no menu, abrir lista e imprimir.

### Implementation for User Story 1

- [X] T003 [US1] Em `app/templates/base.html`, trocar o gate do link "Figurinos" (e da seção
      "Produção") de `eff_has_role('FIGURINO','SUPERADMIN')` para `current_user.is_authenticated`
      (FR-001)

**Checkpoint**: Link de Figurinos visível a todos; lista/impressão já abertas (só login).

---

## Phase 4: User Story 2 - Edição restrita a admin e setor figurino (Priority: P1)

**Goal**: Só SUPERADMIN/FIGURINO criam/editam/excluem/giram foto/sincronizam; UI esconde os
botões para os demais; URL direta recusada.

**Independent Test**: Como usuário sem permissão, botões somem e URLs de edição dão 403;
como FIGURINO/SUPERADMIN, tudo funciona.

### Implementation for User Story 2

- [X] T004 [US2] Em `app/figurino/routes.py`, adicionar `if not _can_edit_figurino(): abort(403)`
      no topo de `new_sheet`, `edit_sheet`, `rotate_photo`, `delete_sheet`, `sync_drive_page` e
      `sync_drive_stream` (antes de qualquer escrita) (FR-003/FR-006)
- [X] T005 [US2] Em `app/templates/figurinos.html`, gate dos botões de edição
      ("+ Nova Ficha", "+ Criar ficha" x2, lápis "Editar", "Sync Drive") com
      `eff_has_role('FIGURINO','SUPERADMIN')`; manter impressão/busca para todos (FR-004/FR-005)

**Checkpoint**: Edição restrita na UI e no servidor; leitura aberta.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T006 Executar `ruff check app/figurino/routes.py` (corrigir o que for novo) e validar
      via test client: usuário sem permissão (lista 200, /new e /edit 403, sem botões);
      FIGURINO/SUPERADMIN (ações 200) — `quickstart.md`

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: diagnóstico.
- **Foundational (Phase 2)**: helper — BLOQUEIA US2.
- **US1 (Phase 3, P1)**: link do menu; independente do helper.
- **US2 (Phase 4, P1)**: depende do helper (T002).
- **Polish (Phase 5)**: depende de tudo.

### Parallel Opportunities

- T003 (`base.html`) é independente de T004 (`figurino/routes.py`) — arquivos diferentes.
- T004 e T005 dependem do conceito de permissão (T002 para o servidor); T005 usa `eff_has_role`.

---

## Implementation Strategy

1. Foundational (helper).
2. US1 (abrir o menu) + US2 (guardas + botões) — ambas P1, indivisíveis na prática
   (abrir a visão sem fechar a edição seria inseguro).
3. **VALIDAR**: `quickstart.md` (visualização aberta, edição 403 para quem não pode).
4. Polish: ruff + verificação no app real.

---

## Notes

- **Sem rota nova, sem migration.** Bônus de segurança: fecha rotas de edição que hoje só
  exigiam login.
- Recusa no servidor (`abort(403)`), não apenas esconder botão.
- Commit atômico após validação (Princípio IV).
