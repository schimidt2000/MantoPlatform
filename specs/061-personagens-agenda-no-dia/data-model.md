# Data Model: Personagens já na agenda no dia (061)

## Mudança no modelo

**Nenhuma.** Sem nova coluna/entidade, sem migration. Consulta apenas leitura.

## Entidades reutilizadas

- **CalendarEvent** — usa `start_at` (dia) e `title` (contexto) e `event_type` (excluir ENSAIO).
- **EventRole** — usa `character_name`, `role_type` (`"character"` = vendável; `"extra"` = apoio)
  e `event_id` (join). `talent_id` **não** é filtro (vaga sem talento já conta).

## Regra de seleção (derivada)

```
personagens_no_dia(data) =
  DISTINCT EventRole.character_name
  WHERE EventRole.role_type = 'character'
    AND EventRole.event.start_at (dia) = data
    AND EventRole.event.event_type <> 'ENSAIO'
  (agrupado por nome; cada um com os títulos dos eventos do dia)
```

## Migração

Nenhuma.
