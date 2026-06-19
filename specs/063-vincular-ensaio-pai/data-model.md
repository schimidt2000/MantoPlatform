# Data Model: Vincular um ensaio existente a um evento pai (063)

## Mudança no modelo

**Nenhuma.** Sem nova coluna/entidade, sem migration.

## Entidade reutilizada

- **CalendarEvent**
  - `parent_event_id` (já existe): passa a poder ser **definido/alterado** depois da criação do
    ensaio, via a nova ação. Relação `parent` / backref `ensaios` reflete o vínculo
    automaticamente.

## Regra (derivada)

```
vincular(ensaio, parent_id):
  exige ensaio.event_type == "ENSAIO"
  exige parent_id válido, parent.event_type != "ENSAIO", parent.id != ensaio.id
  então ensaio.parent_event_id = parent_id
candidate_shows = CalendarEvent where event_type != "ENSAIO" and id != ensaio.id (ordenar por start_at desc)
```

## Migração

Nenhuma.
