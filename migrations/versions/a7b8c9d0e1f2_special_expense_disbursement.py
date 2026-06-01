"""special_expense disbursement fields

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-05-30

Migration escrita à mão (autogenerate quebrado por drift pré-existente do schema).
Adiciona apenas as colunas de desembolso em special_expenses.
"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("special_expenses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("disbursement_type", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("reimburse_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("supplier_name", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("supplier_pix", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("payment_status", sa.String(length=20),
                                      server_default="nao_pago", nullable=False))
        batch_op.create_foreign_key(
            "fk_special_expenses_reimburse_user", "users", ["reimburse_user_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("special_expenses", schema=None) as batch_op:
        batch_op.drop_constraint("fk_special_expenses_reimburse_user", type_="foreignkey")
        batch_op.drop_column("payment_status")
        batch_op.drop_column("supplier_pix")
        batch_op.drop_column("supplier_name")
        batch_op.drop_column("reimburse_user_id")
        batch_op.drop_column("disbursement_type")
