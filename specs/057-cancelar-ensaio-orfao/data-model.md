# Data Model: Cancelar ensaio órfão

## Mudança no modelo

**Nenhuma.** Sem nova coluna, sem nova entidade, sem migration. A feature é puramente de
descoberta (leitura) + exposição de UI, reusando a ação de cancelar já existente.

## Entidades reutilizadas (`CalendarEvent`)

| Campo / Relação | Uso nesta feature |
|---|---|
| `event_type` | `"ENSAIO"` identifica um ensaio. |
| `parent_event_id` / `parent` | Vínculo com o show pai. **Órfão** = `parent is None` (FK nulo ou apontando para show já removido). |
| `google_event_id` | Usado pela rota `delete_ensaio` para remover o ensaio do Google Calendar (já existente). |
| `start_at` / `title` / `description` | Exibição do órfão na lista (data/hora, título, observação). |

## Definição derivada

```
ensaio_órfão  ⇔  event_type == "ENSAIO"  E  parent is None
```

Consulta na home (somente leitura): ensaios (`event_type == "ENSAIO"`) cujo `parent` é
`None`, **sem** filtro de data (inclui passados). Ordenados por `start_at`.

## Ação reutilizada (sem mudança)

`delete_ensaio` (`POST /events/<id>/delete-ensaio`):
- valida `event_type == "ENSAIO"` e RBAC `_CAN_ENSAIO`;
- remove do Google Calendar (aviso se falhar, sem travar);
- `db.session.delete(ensaio)` + commit;
- redireciona ao show pai se existir, senão à home.

## Regras de validação / comportamento

| Regra | Requisito | Comportamento |
|---|---|---|
| Só ensaios | — | Rota recusa (400) se não for `event_type == "ENSAIO"`. |
| RBAC | FR-007 | Rota recusa (403) fora de `_CAN_ENSAIO`; botão não aparece. |
| Não afeta o show pai | FR-004 | Apaga só o ensaio; pai intocado. |
| Confirmação | FR-005 | UI pede confirmação antes do POST. |
| Google ausente/falha | FR-006 | Remove do banco mesmo assim; avisa se o Google falhar. |
| Órfão passado | FR-002 | Aparece na lista (sem filtro de futuro). |

## Migração

Nenhuma.
