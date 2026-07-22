# Tasks: Configurações, Logs, Sync, Desempenho e Migração (168)

**Input**: Design documents from `specs/168-admin-config-react/`
**Tests**: `scripts/db/verify_168_admin_config_react.py` contra `manto_local`.
**Organização**: 4 user stories — US1 configurações (P1), US2 logs/desempenho (P2), US3
sync/anúncio (P3), US4 migração de arquivos/catálogo (P4).

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` atualizado — sem migration nova.

## Phase 2: Foundational

- [X] T002 Criar `app/admin/config_ops.py` (NOVO): `update_settings(settings, **fields)`
      movendo a validação hoje embutida em `admin_settings()`.
- [X] T003 [P] Criar `app/api/admin_config_read.py` / `admin_config_write.py` (NOVO,
      esqueleto): gate `require_superadmin` reimplementado.
- [X] T004 Registrar os 2 módulos em `app/api/__init__.py`.
- [X] T005 [P] Criar `frontend/apps/internal/src/lib/adminConfig.ts` (NOVO, esqueleto).

## Phase 3: User Story 1 — Configurações (P1)

- [X] T006 [US1] Implementar `GET/PATCH /api/admin/settings`.
- [X] T007 [P] [US1] Hooks `useAdminSettings`/`useUpdateAdminSettings`.
- [X] T008 [US1] Criar `AdminSettingsPage.tsx`.
- [X] T009 [US1] Rota `/admin/configuracoes` em `App.tsx`.

## Phase 4: User Story 2 — Logs e desempenho (P2)

- [X] T010 [US2] Implementar `GET /api/admin/logs` e `GET /api/admin/desempenho`.
- [X] T011 [P] [US2] Hooks `useAdminLogs`/`useAdminDesempenho`.
- [X] T012 [US2] Criar `AdminLogsPage.tsx` e `AdminDesempenhoPage.tsx`.
- [X] T013 [US2] Rotas `/admin/logs` e `/admin/desempenho` em `App.tsx`.

## Phase 5: User Story 3 — Sync e anúncio (P3)

- [X] T014 [US3] Implementar `GET /api/admin/sync-status`, `POST /api/admin/sync/run`,
      `POST /api/admin/portal-announcement`.
- [X] T015 [P] [US3] Hooks correspondentes.
- [X] T016 [US3] Criar `AdminSyncPage.tsx` e `AdminPortalAnnouncementPage.tsx`.
- [X] T017 [US3] Rotas `/admin/sync` e `/admin/anuncio-portal` em `App.tsx`.

## Phase 6: User Story 4 — Migração de arquivos e catálogo (P4)

- [X] T018 [US4] Implementar os 4 endpoints de status/start de migração/importação.
- [X] T019 [P] [US4] Hooks correspondentes.
- [X] T020 [US4] Criar `AdminMigrarArquivosPage.tsx` e `AdminImportarCatalogoPage.tsx`.
- [X] T021 [US4] Rotas `/admin/migrar-arquivos` e `/admin/importar-catalogo` em `App.tsx`.

## Phase 7: Polish & Verificação

- [X] T022 Criar `scripts/db/verify_168_admin_config_react.py` (gitignored, mocks p/
      Google/email/threads).
- [X] T023 Rodar `ruff check app/`.
- [X] T024 Rodar `npx tsc --noEmit` e `npm run build`.
- [ ] T025 Conferência mobile — não verificado (sem Playwright).
- [X] T026 Atualizar `docs/changelog.html` e republicar.

## Dependencies

Setup → Foundational → US1..US4 (independentes entre si) → Polish.
