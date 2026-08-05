"""Link de avaliação no Google nas configurações (feedback 5 estrelas).

Revision ID: d9f2b3a41c07
Revises: c17b3ea94f52
Create Date: 2026-08-04
"""

import sqlalchemy as sa
from alembic import op

revision = "d9f2b3a41c07"
down_revision = "c17b3ea94f52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_settings",
        sa.Column("google_review_url", sa.String(length=300), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("site_settings", "google_review_url")
