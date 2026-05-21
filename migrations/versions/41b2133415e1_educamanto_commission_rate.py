"""educamanto commission_rate

Revision ID: 41b2133415e1
Revises: 5330027f6ccc
Create Date: 2026-05-21 01:22:30.054778

"""
from alembic import op
import sqlalchemy as sa


revision = '41b2133415e1'
down_revision = '5330027f6ccc'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('educamanto_packages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('commission_rate', sa.Float(), nullable=False, server_default='0.05'))


def downgrade():
    with op.batch_alter_table('educamanto_packages', schema=None) as batch_op:
        batch_op.drop_column('commission_rate')
