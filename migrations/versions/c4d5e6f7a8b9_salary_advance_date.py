"""Adiantamento de salário: data customizável (feature 120).

Revision ID: c4d5e6f7a8b9
Revises: a2b3c4d5e6f7
Create Date: 2026-07-08
"""

import sqlalchemy as sa
from alembic import op

revision = "c4d5e6f7a8b9"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("salary_advances", sa.Column("advance_date", sa.Date(), nullable=True))
    # Backfill: única data disponível para o histórico já lançado é a de criação do registro.
    op.execute("UPDATE salary_advances SET advance_date = created_at::date WHERE advance_date IS NULL")
    op.alter_column("salary_advances", "advance_date", nullable=False)


def downgrade():
    op.drop_column("salary_advances", "advance_date")
