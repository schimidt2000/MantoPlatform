"""Caixa de avisos de pagamento fora do deploy (feature 340).

Tabela nova ``virtual_payment_inbox``: o ``manto-avisos`` grava o aviso da InfinitePay como chegou
e o backend drena para a fila da 310 (``virtual_payment_notifications``). FK com ``SET NULL``
para o registro que nasceu do dreno; índice parcial nas linhas ainda não drenadas, porque o dreno
roda a cada 10 s em três workers e só olha o que falta.

Aditiva: o código anterior não lê a tabela. Rollback = reverter o merge; o ``downgrade`` só derruba
a tabela.

Revision ID: e340c1a2b3d4
Revises: e339a7c1b2d4
Create Date: 2026-11-10
"""

import sqlalchemy as sa
from alembic import op

revision = "e340c1a2b3d4"
down_revision = "e339a7c1b2d4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "virtual_payment_inbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("secret_ok", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("drained_at", sa.DateTime(), nullable=True),
        sa.Column("notification_id", sa.Integer(), nullable=True),
        sa.Column("alerted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["virtual_payment_notifications.id"],
            name="fk_virtual_payment_inbox_notification_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_virtual_payment_inbox_pendentes",
        "virtual_payment_inbox",
        ["id"],
        postgresql_where=sa.text("drained_at IS NULL"),
    )


def downgrade():
    op.drop_index("ix_virtual_payment_inbox_pendentes", table_name="virtual_payment_inbox")
    op.drop_table("virtual_payment_inbox")
