# Data Model: Múltiplos ensaios + página de ensaio simplificada (062)

## Mudança no modelo

**Nenhuma.** Sem nova coluna/entidade, sem migration.

## Entidades reutilizadas

- **CalendarEvent**
  - Vínculo ensaio→show já existe: `parent_event_id` + relação `parent` / backref **`ensaios`**
    (um-para-muitos). Suporta **vários** ensaios por show sem alteração.
  - `event_type == "ENSAIO"` distingue a página simplificada da página completa de show.
  - Campos exibidos no ensaio: `title`, `start_at`, `end_at`, `location`, `description`,
    `parent` (show de origem).

## Regras (derivadas)

```
show.ensaios           = todos os CalendarEvent com parent_event_id = show.id (ordenar por start_at)
página(ev)             = simplificada  se ev.event_type == "ENSAIO"
                         completa       caso contrário
pode_editar/cancelar   ⇔ usuário em _CAN_ENSAIO (ENSAIO/CASTING/SUPERADMIN)
```

## Migração

Nenhuma.
