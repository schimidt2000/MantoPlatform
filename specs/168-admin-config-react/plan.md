# Implementation Plan: Configurações, Logs, Sync, Desempenho e Ferramentas de Migração (Admin) (168)

**Branch**: `168-admin-config-react` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/168-admin-config-react/spec.md`

## Summary

Quarta fatia da US6. Migra o restante do blueprint `admin` exceto usuários (167, já feita) e
catálogo (169, fatia própria): configurações, logs, sync da agenda, desempenho, anúncio do
portal, migração de arquivos e importação de catálogo (disparo) — 9 rotas no total.

## Technical Context

Igual às fatias 145–167. Sem dependência nova. Verificação com test client Flask contra
`manto_local`, requests fora de `app_context`, mockando Google Calendar/email/threads.

## Constitution Check

- **I (reutilizar)**: sync/limpeza reaproveitam `app.calendar.routes.sync_events`/
  `_mark_month_synced`/`_cleanup_stale_events`/`CALENDAR_ID` e
  `app.calendar.service.fetch_events_for_month`, já existentes, sem duplicar. Migração de
  arquivos e importação de catálogo reaproveitam `drive_migration.migration_status`/
  `start_background_migration` e `catalogo.importer.import_status`/`start_background_import`,
  já puros — nenhum controle de concorrência novo. Só o núcleo de **configurações** (validação
  de campos) é novo o bastante para extrair (`app/admin/config_ops.py`).
- **II**: `config_ops.py` novo com type hints/docstrings; endpoints em
  `app/api/admin_config_read.py`/`admin_config_write.py`.
- **III**: endpoints novos 100% JSON; views Jinja continuam em paralelo (FR-008).
- **IV**: paridade verificada contra `manto_local`, Google Calendar/email/threads mockados.
- **V**: loading/erro/sucesso via TanStack Query; resultados de sync/limpeza/anúncio mostrados
  como lista de resultado por item (mesma informação da tela antiga).
- **VIII/IX**: mobile-first e transições padrão, sem novidade além do já estabelecido.

Sem violação nova.

## Project Structure

```text
app/admin/config_ops.py                 # NOVO — validação/atualização de SiteSetting
app/api/admin_config_read.py            # NOVO — GET settings/logs/desempenho/sync-status/
                                         #   migrar-arquivos-status/importar-catalogo-status
app/api/admin_config_write.py           # NOVO — PATCH settings; POST sync/cleanup/anuncio/
                                         #   migrar-arquivos/importar-catalogo
app/api/__init__.py                     # + import dos 2 módulos
frontend/apps/internal/src/
├── lib/adminConfig.ts                  # NOVO — hooks
├── pages/AdminSettingsPage.tsx         # NOVO
├── pages/AdminLogsPage.tsx             # NOVO
├── pages/AdminDesempenhoPage.tsx       # NOVO
├── pages/AdminSyncPage.tsx             # NOVO
├── pages/AdminPortalAnnouncementPage.tsx  # NOVO
├── pages/AdminMigrarArquivosPage.tsx   # NOVO
└── pages/AdminImportarCatalogoPage.tsx # NOVO
App.tsx                                 # + 7 rotas /admin/*
scripts/db/verify_168_admin_config_react.py  # NOVO
```

**Structure Decision**: só `config_ops.py` é extraído (única lógica de validação nova); as
demais 8 rotas viram endpoints finos sobre helpers já existentes e puros em outros módulos
(`app.calendar`, `app.drive_migration`, `app.catalogo.importer`, `app.email_service`).

## Design Decisions

1. **`GET /api/admin/settings`** / **`PATCH /api/admin/settings`** (multipart quando há logo):
   `config_ops.update_settings(settings, **campos)` aplica as mesmas tolerâncias de hoje (campo
   inválido é ignorado, não bloqueia o resto).
2. **`GET /api/admin/logs`**: querystring `entity_type`/`actor`/`page`, mesma paginação (50/pg).
3. **`GET /api/admin/desempenho`**: querystring `month` (`YYYY-MM`), mesmo fallback de hoje.
4. **`GET /api/admin/sync-status`** / **`POST /api/admin/sync/run`** (`action`:
   `sync_now`|`cleanup_past`): reaproveita exatamente as duas árvores de decisão de
   `sync_status()` hoje, movidas para o endpoint (helpers de `app.calendar` já são a fonte
   única — só a orquestração migra).
5. **`POST /api/admin/portal-announcement`**: reaproveita `send_portal_announcement_email`.
6. **`GET /api/admin/migrar-arquivos/status`** / **`POST /api/admin/migrar-arquivos/start`**:
   reaproveita `drive_migration.migration_status`/`start_background_migration` sem alteração.
7. **`GET /api/admin/importar-catalogo/status`** / **`POST /api/admin/importar-catalogo/start`**:
   reaproveita `catalogo.importer.import_status`/`start_background_import` sem alteração.
8. Todos os 9 endpoints usam o mesmo gate `require_superadmin` reimplementado como função.

## Complexity Tracking

Nenhuma violação nova.
