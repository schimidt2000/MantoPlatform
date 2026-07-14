"""Gasto extra já nasce pago: flag paid_at_creation em special_expenses (feature 128).

Revision ID: 9ae0a236db40
Revises: 73a573f58c1d
Create Date: 2026-07-14
"""

import sqlalchemy as sa
from alembic import op

revision = "9ae0a236db40"
down_revision = "73a573f58c1d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "special_expenses",
        sa.Column("paid_at_creation", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("special_expenses", "paid_at_creation")
