# Data Model: Pipeline de Vendas em React (156)

Nenhuma tabela/campo novo — reaproveita `CalendarEvent` já existente. Esta fatia só adiciona
uma serialização de leitura sobre campos que já existiam.

## Campos lidos de `CalendarEvent` (`app/models.py:206`)

| Campo/propriedade    | Uso                                                    |
|-----------------------|---------------------------------------------------------|
| `title`                | título do evento                                        |
| `start_at`             | data do evento (ordenação e coluna "Data evento")        |
| `location`             | local                                                    |
| `sale_date`            | data da venda                                            |
| `sale_value`           | valor da venda                                           |
| `event_type`           | filtro (exclui `ENSAIO`)                                 |
| `with_invoice`         | indicador de NF                                          |
| `is_satellite`         | pula a linha (consolidada no principal)                  |
| `is_group_leader`      | mostra nome do grupo em vez do título                    |
| `group_display_name`   | nome do grupo comercial                                  |
| `satellites`           | usado por `_group_cost` para somar custo do grupo         |
| `is_educamanto`        | filtro do responsável EducaManto sem papéis plenos        |
| `roles` (via `EventRole`) | usado por `_event_cost`/`_group_cost` (soma de cachês) |

## Valores computados (reaproveitados de `app/financeiro/routes.py`, sem duplicar)

- `custo` = `_group_cost(event)` se `is_group_leader`, senão `_event_cost(event)`.
- `comissao` = `_event_commission(event, settings)`.
- `lucro` = `sale_value − custo` (só na resposta quando `is_financeiro`).
