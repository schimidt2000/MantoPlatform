"""Frequência e vigência dos gastos recorrentes (feature 112).

recurring_expenses ganha frequency (mensal|semanal|quinzenal|anual), start_date
(backfill = data de criação) e end_date (NULL = eterna).

Revision ID: a7b8c9d0e1f3
Revises: f6a7b8c9d0e1
Create Date: 2026-07-06
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f3"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "recurring_expenses",
        sa.Column("frequency", sa.String(20), nullable=False, server_default="mensal"),
    )
    op.add_column("recurring_expenses", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("recurring_expenses", sa.Column("end_date", sa.Date(), nullable=True))
    # Contas existentes: mensais eternas desde a criação (FR-006).
    op.execute("UPDATE recurring_expenses SET start_date = created_at::date WHERE start_date IS NULL")
    op.alter_column("recurring_expenses", "start_date", nullable=False)


def downgrade():
    op.drop_column("recurring_expenses", "end_date")
    op.drop_column("recurring_expenses", "start_date")
    op.drop_column("recurring_expenses", "frequency")
