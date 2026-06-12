"""event_payments.amount: Integer -> Numeric(12,2)

Revision ID: l8a9b0c1d2e3
Revises: k7e8f9a0b1c2
Create Date: 2026-06-12

O valor recebido era gravado como inteiro (reais), arredondando os centavos
digitados (ex.: 10.996,25 -> 10.996) e deixando um falso "Falta R$ 0,25".
Passa a Numeric(12,2), mesma precisão de sale_value. Valores antigos
(inteiros) convertem sem perda.
"""
import sqlalchemy as sa
from alembic import op

revision = "l8a9b0c1d2e3"
down_revision = "k7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("event_payments") as batch_op:
        batch_op.alter_column(
            "amount",
            existing_type=sa.Integer(),
            type_=sa.Numeric(12, 2),
            existing_nullable=True,
        )


def downgrade():
    with op.batch_alter_table("event_payments") as batch_op:
        batch_op.alter_column(
            "amount",
            existing_type=sa.Numeric(12, 2),
            type_=sa.Integer(),
            existing_nullable=True,
        )
