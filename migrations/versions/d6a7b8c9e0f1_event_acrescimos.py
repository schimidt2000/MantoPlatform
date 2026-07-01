"""event_acrescimos — acréscimos tipados com BV (feature 099)

Revision ID: d6a7b8c9e0f1
Revises: c5f6a7b8d9e0
Create Date: 2026-07-01

Cria a tabela event_acrescimos (acréscimos tipados por evento). O tipo "BV" é um repasse: não é lucro nem
comissão e vira pagamento com PIX. O campo legado calendar_events.acrescimo_value é preservado (tratado
como acréscimo comum).

Migration escrita a mão (autogenerate quebrado por drift pré-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "d6a7b8c9e0f1"
down_revision = "c5f6a7b8d9e0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "event_acrescimos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=True),
        sa.Column("is_percent", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("value", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("amount_brl", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("is_bv", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("bv_recipient", sa.String(length=200), nullable=True),
        sa.Column("bv_pix", sa.String(length=140), nullable=True),
        sa.Column("bv_payment_status", sa.String(length=20), nullable=False, server_default="nao_pago"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["calendar_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_acrescimos_event_id", "event_acrescimos", ["event_id"], unique=False)


def downgrade():
    op.drop_index("ix_event_acrescimos_event_id", table_name="event_acrescimos")
    op.drop_table("event_acrescimos")
