"""cronograma de parcelas + data de emissão da NF (feature 065)

Revision ID: t6c7d8e9f0a1
Revises: s5b6c7d8e9f0
Create Date: 2026-06-19

Adiciona:
- Tabela event_installments: cronograma de recebimentos planejados por evento
  (due_date + amount + received). Distinta de event_payments (comprovante).
- calendar_events.invoice_due_date (Date, nullable): data prevista de emissão da NF.

A receita reconhecida no painel NÃO muda (segue pela data do evento); estas estruturas
alimentam apenas as visões informativas de recebimentos previstos e NF a emitir.

Migration escrita à mão (autogenerate quebrado por drift pré-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "t6c7d8e9f0a1"
down_revision = "s5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "event_installments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("received", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["calendar_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_installments_event_id", "event_installments", ["event_id"], unique=False
    )
    with op.batch_alter_table("calendar_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("invoice_due_date", sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table("calendar_events", schema=None) as batch_op:
        batch_op.drop_column("invoice_due_date")
    op.drop_index("ix_event_installments_event_id", table_name="event_installments")
    op.drop_table("event_installments")
