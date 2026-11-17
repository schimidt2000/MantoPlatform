"""Parcelas do pagamento de um gasto extra (feature 353).

Aditiva: ``gasto_parcelas`` — uma linha por parcela, com data, valor e a própria situação de pagamento. Some com o
gasto (CASCADE). Nenhum gasto existente muda: sem parcelas, o gasto segue um pagamento só.

O ``downgrade`` derruba a tabela; o ``amount`` dos gastos parcelados fica com a soma, e a Planilha volta a mostrá-los
inteiros na ``expense_date``.

Revision ID: f353a1b2c3d4
Revises: f352a1b2c3d4
Create Date: 2026-11-17
"""

import sqlalchemy as sa
from alembic import op

revision = "f353a1b2c3d4"
down_revision = "f352a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gasto_parcelas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "special_expense_id",
            sa.Integer(),
            sa.ForeignKey(
                "special_expenses.id",
                name="fk_gasto_parcelas_special_expense_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_status", sa.String(20), nullable=False, server_default="nao_pago"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("special_expense_id", "numero", name="uq_gasto_parcelas_gasto_numero"),
        sa.CheckConstraint("valor > 0", name="ck_gasto_parcelas_valor_positivo"),
    )
    op.create_index(
        "ix_gasto_parcelas_special_expense_id", "gasto_parcelas", ["special_expense_id"]
    )
    op.create_index("ix_gasto_parcelas_data", "gasto_parcelas", ["data"])


def downgrade():
    op.drop_index("ix_gasto_parcelas_data", table_name="gasto_parcelas")
    op.drop_index("ix_gasto_parcelas_special_expense_id", table_name="gasto_parcelas")
    op.drop_table("gasto_parcelas")
