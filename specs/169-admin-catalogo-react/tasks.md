# Tasks: Gestão de Catálogo (169)

**Tests**: `scripts/db/verify_169_admin_catalogo_react.py` contra `manto_local`.
**Organização**: 4 user stories — US1 listar (P1), US2 criar (P2), US3 editar (P3), US4
ativar/excluir (P4).

## Phase 1: Setup
- [X] T001 Confirmar `manto_local` atualizado.

## Phase 2: Foundational
- [X] T002 Criar `app/admin/catalog_ops.py` (NOVO): mover núcleo de fotos/tags/categoria de
      `app/admin/routes.py`.
- [X] T003 [P] Criar `app/api/admin_catalogo_read.py`/`admin_catalogo_write.py` (esqueleto).
- [X] T004 Registrar em `app/api/__init__.py`.
- [X] T005 [P] Criar `frontend/apps/internal/src/lib/adminCatalogo.ts` (esqueleto).

## Phase 3: US1 — Listar (P1)
- [X] T006 [US1] `GET /api/admin/catalogo`.
- [X] T007 [P] [US1] Hook `useAdminCatalogo(filters)`.
- [X] T008 [US1] `AdminCatalogoListPage.tsx`.
- [X] T009 [US1] Rota `/admin/catalogo`.

## Phase 4: US2 — Criar categoria e produto (P2)
- [X] T010 [US2] `POST /api/admin/catalogo/categorias`, `POST /api/admin/catalogo`,
      `GET /api/admin/catalogo/<id>`.
- [X] T011 [P] [US2] Hooks correspondentes.
- [X] T012 [US2] `AdminCatalogoFormPage.tsx` (modo criar).
- [X] T013 [US2] Rota `/admin/catalogo/novo`.

## Phase 5: US3 — Editar (P3)
- [X] T014 [US3] `PATCH /api/admin/catalogo/<id>`.
- [X] T015 [P] [US3] Hook de atualização.
- [X] T016 [US3] `AdminCatalogoFormPage.tsx` (modo editar: fotos existentes, mover, capa,
      remover).
- [X] T017 [US3] Rota `/admin/catalogo/:id/editar`.

## Phase 6: US4 — Ativar/excluir (P4)
- [X] T018 [US4] `POST /api/admin/catalogo/<id>/toggle-ativo`, `DELETE /api/admin/catalogo/<id>`.
- [X] T019 [P] [US4] Hooks correspondentes.
- [X] T020 [US4] Botões na lista/form.

## Phase 7: Polish
- [X] T021 Criar `scripts/db/verify_169_admin_catalogo_react.py`.
- [X] T022 `ruff check app/`.
- [X] T023 `npx tsc --noEmit` e `npm run build`.
- [ ] T024 Conferência mobile — não verificado (sem Playwright).
- [X] T025 Atualizar `docs/changelog.html` e republicar.

## Dependencies
Setup → Foundational → US1 → US2 → US3 → US4 → Polish.
