"""client feedback name (feature 132)

Revision ID: 4e2bdfa8b106
Revises: d969149662f5
Create Date: 2026-07-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4e2bdfa8b106"
down_revision = "d969149662f5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "client_feedbacks",
        sa.Column("client_name", sa.String(length=200), nullable=True),
    )


def downgrade():
    op.drop_column("client_feedbacks", "client_name")
