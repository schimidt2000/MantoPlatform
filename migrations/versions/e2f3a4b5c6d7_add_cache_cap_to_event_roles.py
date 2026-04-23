"""add cache_cap to event_roles

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-04-22

"""
from alembic import op
import sqlalchemy as sa

revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'event_roles',
        sa.Column('cache_cap', sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column('event_roles', 'cache_cap')
