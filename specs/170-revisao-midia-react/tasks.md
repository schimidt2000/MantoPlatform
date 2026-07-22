# Tasks: Revisão de Mídia (170)

**Tests**: `scripts/db/verify_170_revisao_midia_react.py` contra `manto_local`.
**Organização**: 4 user stories — US1 listar/criar espaço (P1), US2 gerenciar espaço (P2), US3
visualizar/comentar (P3), US4 substituir/finalizar (P4).

## Phase 1: Setup
- [X] T001 Confirmar `manto_local` atualizado.

## Phase 2: Foundational
- [X] T002 Criar `app/revisao/review_ops.py` (NOVO): mover núcleo de permissões, upload,
      snapshot de versão, comentários de `app/revisao/routes.py`.
- [X] T003 [P] Criar `app/api/revisao_read.py`/`revisao_write.py` (esqueleto).
- [X] T004 Registrar em `app/api/__init__.py`.
- [X] T005 [P] Criar `frontend/apps/internal/src/lib/revisao.ts` (esqueleto).

## Phase 3: US1 — Listar e criar espaço (P1)
- [X] T006 [US1] `GET /api/revisao`, `POST /api/revisao` (multipart).
- [X] T007 [P] [US1] Hooks `useRevisaoSpaces()`/`useCreateRevisaoSpace()`.
- [X] T008 [US1] `RevisaoListPage.tsx`, `RevisaoSpaceCreatePage.tsx`.
- [X] T009 [US1] Rotas `/revisao`, `/revisao/novo`.

## Phase 4: US2 — Gerenciar espaço (P2)
- [X] T010 [US2] `GET /api/revisao/<id>`, `POST /api/revisao/<id>/upload`,
      `PATCH /api/revisao/<id>/reviewers`, `DELETE /api/revisao/<id>`.
- [X] T011 [P] [US2] Hooks correspondentes.
- [X] T012 [US2] `RevisaoSpacePage.tsx`.
- [X] T013 [US2] Rota `/revisao/:id`.

## Phase 5: US3 — Visualizar e comentar (P3)
- [X] T014 [US3] `GET /api/revisao/<space_id>/asset/<asset_id>`,
      `GET/POST /api/revisao/asset/<asset_id>/comment(s)`,
      `POST /api/revisao/comment/<id>/resolve`, `DELETE /api/revisao/comment/<id>`.
- [X] T015 [P] [US3] Hooks correspondentes.
- [X] T016 [US3] `RevisaoAssetPage.tsx` (players nativos + lista de comentários).
- [X] T017 [US3] Rota `/revisao/:spaceId/asset/:assetId`.

## Phase 6: US4 — Substituir/finalizar (P4)
- [X] T018 [US4] `DELETE /api/revisao/asset/<id>`, `POST .../replace`, `POST .../finalize`.
- [X] T019 [P] [US4] Hooks correspondentes.
- [X] T020 [US4] Seções de substituir/finalizar/excluir em `RevisaoAssetPage.tsx`.

## Phase 7: Polish
- [X] T021 Criar `scripts/db/verify_170_revisao_midia_react.py`.
- [X] T022 `ruff check app/`.
- [X] T023 `npx tsc --noEmit` e `npm run build`.
- [ ] T024 Conferência mobile — não verificado (sem Playwright).
- [X] T025 Atualizar `docs/changelog.html` e republicar.

## Dependencies
Setup → Foundational → US1 → US2 → US3 → US4 → Polish.
