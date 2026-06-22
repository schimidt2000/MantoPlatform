"""adiantamento de salario: salary_payments.advance_amount + advance_proof (feature 067)

Revision ID: u7d8e9f0a1b2
Revises: t6c7d8e9f0a1
Create Date: 2026-06-20

Adiciona em salary_payments:
- advance_amount (Numeric(12,2), nullable): valor ja pago antecipadamente.
- advance_proof (String(300), nullable): caminho do comprovante do adiantamento.

O valor a pagar passa a ser o liquido (amount - advance_amount); o custo de salario do
balanco continua usando amount cheio (adiantamento e caixa, nao custo).

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "u7d8e9f0a1b2"
down_revision = "t6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("salary_payments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("advance_amount", sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column("advance_proof", sa.String(length=300), nullable=True))


def downgrade():
    with op.batch_alter_table("salary_payments", schema=None) as batch_op:
        batch_op.drop_column("advance_proof")
        batch_op.drop_column("advance_amount")
