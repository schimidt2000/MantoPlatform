"""add invoice_file to calendar_events

Revision ID: d1e2f3a4b5c6
Revises: c2d3e4f5a6b7
Create Date: 2026-04-22

"""
from alembic import op
import sqlalchemy as sa

revision = 'd1e2f3a4b5c6'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'calendar_events',
        sa.Column('invoice_file', sa.String(length=255), nullable=True),
    )


def downgrade():
    op.drop_column('calendar_events', 'invoice_file')
