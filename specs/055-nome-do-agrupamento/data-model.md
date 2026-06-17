# Data Model: Nome do agrupamento de eventos

## Mudança no modelo

Uma única adição em `CalendarEvent` (tabela `calendar_events`). Sem nova tabela/entidade.

### Novo campo

| Campo | Tipo | Nulo | Origem | Uso |
|---|---|---|---|---|
| `group_name` | `String(200)` | sim (nullable) | **055** | Nome do grupo, preenchido no evento **principal**. Em satélites permanece `NULL` (não usado). |

### Nova propriedade derivada (fonte única do rótulo)

```python
@property
def group_display_name(self) -> str:
    """Rótulo do grupo para exibição: o nome do grupo, ou o título do evento (fallback)."""
    return self.group_name or self.title
```

- Consumida por: home comercial, painel financeiro (tabela de eventos), pipeline de vendas,
  e tela de detalhe (banner de satélite + seção do principal).

## Campos/relações reutilizados (053/054)

| Campo / Relação | Uso nesta feature |
|---|---|
| `group_leader_id` (FK self) | Identifica satélites; filtro para ocultá-los na home e no balanço. |
| `group_leader` / `satellites` | Navegação principal↔satélites (inalterada). |
| `is_satellite` / `is_group_leader` (props) | Decidir exibição (banner, ocultar satélite, mostrar nome no principal). |
| `sale_value` | Já `NULL` no satélite (zerado ao agrupar) — base da consolidação comercial. |

## Regras de validação / comportamento

| Regra | Requisito | Comportamento |
|---|---|---|
| Nome é opcional | FR-001/FR-003 | Sem nome → exibe `title` (fallback) via `group_display_name`. |
| Nome pertence ao grupo (principal) | Edge case | Só editável no evento principal; satélites não editam nome. |
| Definir nome ao agrupar | FR-002 | `_handle_group_events` lê `group_name` (opcional) e salva no líder. |
| Editar/limpar nome depois | FR-002 / edge case | Ação `rename_group`; nome vazio volta ao fallback. |
| RBAC | FR-009 | Definir/editar restrito a COMERCIAL/FINANCEIRO/SUPERADMIN (`_can_group_events`). |
| Comprimento | Edge case | `String(200)`; truncar/quebrar no layout. |

## Migração

- Manual: `..._group_name.py`, `down_revision = q3f4a5b6c7d8`.
- `upgrade`: `batch_alter_table("calendar_events").add_column(Column("group_name", String(200), nullable=True))`.
- `downgrade`: `drop_column("group_name")`.
- **Sem migração de dados**: campo novo nasce `NULL`; grupos existentes (053/054) passam a
  exibir o título do principal como rótulo até receberem um nome.
