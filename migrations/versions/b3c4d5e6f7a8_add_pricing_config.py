"""add pricing_config to site_settings

Revision ID: b3c4d5e6f7a8
Revises: a9240eaf2fe1
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f7a8'
down_revision = 'a9240eaf2fe1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pricing_config', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('pricing_config')
