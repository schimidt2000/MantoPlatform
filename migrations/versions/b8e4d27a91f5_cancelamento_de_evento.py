"""Cancelamento de evento e solicitação de exclusão (feature 224).

Evento com dinheiro preso (pagamento recebido, contrato, elenco escalado) deixa de ser apagado
e passa a ser **cancelado**: o registro fica, some de toda métrica, e é a ele que a devolução
ao cliente se refere. A solicitação de exclusão existe porque o Comercial perdeu a permissão de
excluir — ele pede, o Superadmin decide.

Todos os campos nascem nulos, então a migração não muda o comportamento de nenhum evento
existente: sem `cancelled_at`, tudo segue contando como hoje.

Revision ID: b8e4d27a91f5
Revises: a3f7c19d5e02
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op

revision = "b8e4d27a91f5"
down_revision = "a3f7c19d5e02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calendar_events", sa.Column("cancelled_at", sa.DateTime(), nullable=True))
    op.add_column("calendar_events", sa.Column("cancelled_by_id", sa.Integer(), nullable=True))
    op.add_column("calendar_events", sa.Column("cancellation_reason", sa.Text(), nullable=True))
    op.add_column(
        "calendar_events", sa.Column("deletion_requested_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "calendar_events", sa.Column("deletion_requested_by_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "calendar_events", sa.Column("deletion_request_reason", sa.Text(), nullable=True)
    )
    op.create_foreign_key(
        "fk_calendar_events_cancelled_by", "calendar_events", "users",
        ["cancelled_by_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_calendar_events_deletion_requested_by", "calendar_events", "users",
        ["deletion_requested_by_id"], ["id"],
    )
    # Toda query de métrica passa a filtrar por `cancelled_at IS NULL`; o índice parcial mantém
    # esse filtro barato sem inchar o índice com as linhas canceladas (que são a minoria).
    op.create_index(
        "ix_calendar_events_cancelled_at", "calendar_events", ["cancelled_at"],
        postgresql_where=sa.text("cancelled_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_calendar_events_cancelled_at", table_name="calendar_events")
    op.drop_constraint(
        "fk_calendar_events_deletion_requested_by", "calendar_events", type_="foreignkey"
    )
    op.drop_constraint("fk_calendar_events_cancelled_by", "calendar_events", type_="foreignkey")
    op.drop_column("calendar_events", "deletion_request_reason")
    op.drop_column("calendar_events", "deletion_requested_by_id")
    op.drop_column("calendar_events", "deletion_requested_at")
    op.drop_column("calendar_events", "cancellation_reason")
    op.drop_column("calendar_events", "cancelled_by_id")
    op.drop_column("calendar_events", "cancelled_at")
