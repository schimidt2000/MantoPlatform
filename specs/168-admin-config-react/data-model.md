# Data Model: Configurações, Logs, Sync, Desempenho e Migração (168)

Nenhuma tabela/campo novo.

| Entidade      | Uso                                                                    |
|---------------|--------------------------------------------------------------------------|
| `SiteSetting` | registro único (id=1) — configurações gerais, lido/escrito nesta fatia   |
| `AuditLog`    | logs de auditoria (leitura paginada, filtro por tipo/ator)               |
| `EventLog`    | estatísticas de desempenho (casting/figurino por pessoa)                 |
| `CalendarEvent` | vendas por vendedor (desempenho); meses com eventos (status de sync)   |
| `Talent`      | contagem de arquivos pendentes de migração (Drive→volume)                |
| `CatalogItem` | contagem de itens já importados (status de importação de catálogo)      |

## Valores computados (reaproveitados sem duplicar)

- `config_ops.update_settings(settings, **fields)` — mesma tolerância de hoje: campo numérico
  inválido é ignorado; upload de logo só troca `logo_path` se o arquivo tiver extensão aceita.
- Sync/limpeza: `app.calendar.routes.sync_events`/`_mark_month_synced`/`_cleanup_stale_events`,
  `app.calendar.service.fetch_events_for_month` — mesmas funções já usadas pela sincronização
  automática (cron interno), reaproveitadas sem alteração.
- Migração/importação: `drive_migration.migration_status`/`start_background_migration`,
  `catalogo.importer.import_status`/`start_background_import` — dicionários compartilhados
  (thread-safe via lock interno), já a fonte única de status; endpoints só leem/disparam.
