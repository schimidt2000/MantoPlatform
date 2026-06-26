"""lista de adiantamentos de salario (feature 089)

Revision ID: y1b2c3d4e5f6
Revises: x0a1b2c3d4e5
Create Date: 2026-06-26

Cria a tabela salary_advances (varios adiantamentos por salary_payment) e importa os adiantamentos
unicos ja existentes (salary_payments.advance_amount nao nulo) como um item da nova lista. As colunas
legadas advance_amount/advance_proof sao mantidas (nao mais usadas pelo codigo).

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "y1b2c3d4e5f6"
down_revision = "x0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "salary_advances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("salary_payment_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("proof", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["salary_payment_id"], ["salary_payments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_salary_advances_payment_id", "salary_advances", ["salary_payment_id"], unique=False
    )
    # Importa os adiantamentos unicos existentes para a nova lista.
    op.execute(
        """
        INSERT INTO salary_advances (salary_payment_id, amount, proof, created_at)
        SELECT id, advance_amount, advance_proof, COALESCE(created_at, CURRENT_TIMESTAMP)
        FROM salary_payments
        WHERE advance_amount IS NOT NULL
        """
    )


def downgrade():
    op.drop_index("ix_salary_advances_payment_id", table_name="salary_advances")
    op.drop_table("salary_advances")
