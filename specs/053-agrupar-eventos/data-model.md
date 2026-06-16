# Data Model: Agrupamento de Eventos por Contrato

**Feature**: 053-agrupar-eventos | **Date**: 2026-06-16

## Alterações em `CalendarEvent` (`app/models.py`)

| Campo | Tipo | Nullable | Descrição |
|---|---|---|---|
| `group_leader_id` | `Integer`, FK → `calendar_event.id` | Sim (default) | Quando preenchido, este evento é **satélite** do evento cujo `id` está aqui. Quando `NULL`, o evento é independente ou é **principal** (ver propriedade `is_group_leader`). |

Relacionamento SQLAlchemy:

```python
group_leader_id: Mapped[Optional[int]] = mapped_column(
    db.Integer, db.ForeignKey("calendar_event.id"), nullable=True
)
group_leader: Mapped[Optional["CalendarEvent"]] = db.relationship(
    "CalendarEvent",
    remote_side="CalendarEvent.id",
    foreign_keys=[group_leader_id],
    backref="satellites",
)
```

- `event.group_leader` → o evento principal (ou `None` se independente/principal).
- `event.satellites` → lista de eventos satélites (vazia se este evento não é principal de ninguém).

### Propriedades derivadas (não persistidas)

```python
@property
def is_satellite(self) -> bool:
    """True se este evento é satélite de outro (campos comerciais herdados)."""
    return self.group_leader_id is not None

@property
def is_group_leader(self) -> bool:
    """True se este evento é principal de pelo menos um satélite."""
    return len(self.satellites) > 0
```

### Campos comerciais afetados (zerados ao se tornar satélite — FR-005)

`sale_value`, `sale_value_gross`, `sale_date`, `with_invoice`,
`is_cortesia_permuta`, `seller_id`, `commission_rate`, `payment_method`,
`payment_installments`, `payment_due_date`, `transport_value`,
`acrescimo_value`, `invoice_file`, `orcamento_history_id`.

Estes campos **não são removidos do modelo** — apenas zerados/nulificados no
momento do agrupamento. Ao desfazer o agrupamento (FR-008), o evento volta a
ter esses campos editáveis (permanecem com os valores zerados, não há
restauração automática do valor anterior — já avisado ao usuário na
confirmação, FR-005).

## Validações (camada de rotas, `app/calendar/routes.py`)

| Regra | Origem |
|---|---|
| Não permitir `group_leader_id == self.id` | FR-004 |
| Não permitir agrupar evento que já é satélite (`event.is_satellite`) sem desagrupar primeiro | FR-002 |
| Não permitir agrupar evento que já é principal (`event.is_group_leader`) como satélite de outro | Assumptions — estrutura plana de 2 níveis |
| Não permitir agrupar evento `event_type == "ENSAIO"` | FR-003 |
| Não permitir excluir evento com `is_group_leader == True` sem antes desagrupar satélites | FR-009 |

## Auditoria (FR-015)

Reaproveita o mecanismo de log já existente no projeto (mesmo padrão usado
para outras ações administrativas — confirmar nome exato do helper/model de
log durante a implementação, ex. `AuditLog` se existir, ou logging padrão
Python para arquivo se não houver tabela de auditoria). Registro mínimo:
usuário responsável, ação (`group` / `ungroup`), `event_id` do satélite,
`group_leader_id` envolvido, timestamp.

## Sem novas tabelas

Conforme spec (Key Entities — "Grupo de eventos" é implícito), não há
`EventGroup` nem tabela associativa. O grupo é inteiramente representado pela
coluna `group_leader_id` e pelo relacionamento `satellites`.

## Sem migração de dados existentes

Todos os eventos existentes recebem `group_leader_id = NULL` por padrão
(coluna nova, nullable) — comportamento idêntico ao atual, sem necessidade de
backfill.
