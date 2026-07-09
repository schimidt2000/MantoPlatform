"""Pagamento programado: remove limite de 1 lançamento/mês por conta (feature 121).

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-09
"""

from alembic import op

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("uq_recurring_entry_month", "recurring_expense_entries", type_="unique")


def downgrade():
    op.create_unique_constraint(
        "uq_recurring_entry_month", "recurring_expense_entries", ["recurring_id", "month_ref"]
    )
