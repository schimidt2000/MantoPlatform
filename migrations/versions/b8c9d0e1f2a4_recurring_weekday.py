"""Dia da semana explícito nas contas recorrentes semanais (feature 113).

recurring_expenses.weekday: 0=segunda … 6=domingo (só frequência semanal). Backfill das
semanais existentes com o dia da semana da data de início (ISODOW 1–7 → 0–6).

Revision ID: b8c9d0e1f2a4
Revises: a7b8c9d0e1f3
Create Date: 2026-07-06
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8c9d0e1f2a4"
down_revision = "a7b8c9d0e1f3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recurring_expenses", sa.Column("weekday", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE recurring_expenses "
        "SET weekday = EXTRACT(ISODOW FROM start_date)::int - 1 "
        "WHERE frequency = 'semanal' AND weekday IS NULL"
    )


def downgrade():
    op.drop_column("recurring_expenses", "weekday")
