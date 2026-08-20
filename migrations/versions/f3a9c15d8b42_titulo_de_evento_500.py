"""Título de evento (e suas cópias) de 200 para 500 caracteres (feature 254).

Incidente real de 20/08: um evento CORP cujo título lista o elenco inteiro ("(CORP) SOLDADO 1
BONECO + SOLDADO 2 BONECO + PINGUINO + ...") passa de 200 caracteres e a criação morre com
`StringDataRightTruncation` — DEPOIS de já ter criado o evento no Google, deixando órfão lá.
Títulos assim são prática da casa (o elenco no título é como a equipe busca na agenda), então a
coluna acompanha, e as colunas que recebem CÓPIA do título vão juntas — senão o estouro só muda
de endereço:

- `calendar_events.title` — a origem;
- `calendar_events.location` — mesmo risco, endereços completos do autocomplete do Google;
- `audit_logs.entity_name` — recebe `event.title` em todo `_log_sync`;
- `commission_payments.event_title` — cópia que persiste após exclusão do evento.

Alargamento puro (nenhum dado é tocado, nenhum índice recriado). O teto novo tem guarda de
validação em `_validate_event_core` (480 no título digitado, sobrando espaço para o prefixo
"(TIPO) ") — erro de campo amigável em vez de 500.

Revision ID: f3a9c15d8b42
Revises: e2d8ca4b3071
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "f3a9c15d8b42"
down_revision = "e2d8ca4b3071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "calendar_events", "title",
        existing_type=sa.String(length=200), type_=sa.String(length=500),
        existing_nullable=False,
    )
    op.alter_column(
        "calendar_events", "location",
        existing_type=sa.String(length=200), type_=sa.String(length=500),
        existing_nullable=True,
    )
    op.alter_column(
        "audit_logs", "entity_name",
        existing_type=sa.String(length=200), type_=sa.String(length=500),
        existing_nullable=True,
    )
    op.alter_column(
        "commission_payments", "event_title",
        existing_type=sa.String(length=200), type_=sa.String(length=500),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Estreitar de volta TRUNCARIA títulos já gravados acima de 200 — por isso o downgrade
    # corta explicitamente antes, para o ALTER não falhar no meio.
    for table, column in (
        ("calendar_events", "title"),
        ("calendar_events", "location"),
        ("audit_logs", "entity_name"),
        ("commission_payments", "event_title"),
    ):
        op.execute(f"UPDATE {table} SET {column} = LEFT({column}, 200) WHERE LENGTH({column}) > 200")
    op.alter_column(
        "calendar_events", "title",
        existing_type=sa.String(length=500), type_=sa.String(length=200),
        existing_nullable=False,
    )
    op.alter_column(
        "calendar_events", "location",
        existing_type=sa.String(length=500), type_=sa.String(length=200),
        existing_nullable=True,
    )
    op.alter_column(
        "audit_logs", "entity_name",
        existing_type=sa.String(length=500), type_=sa.String(length=200),
        existing_nullable=True,
    )
    op.alter_column(
        "commission_payments", "event_title",
        existing_type=sa.String(length=500), type_=sa.String(length=200),
        existing_nullable=False,
    )
