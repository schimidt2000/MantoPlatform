"""add calendar_sync_cache to site_settings

Revision ID: 1e617e199087
Revises: 41b2133415e1
Create Date: 2026-05-21 11:26:13.610826

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1e617e199087'
down_revision = '41b2133415e1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('calendar_sync_cache', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('calendar_sync_cache')
