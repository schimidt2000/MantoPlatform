"""add_change_description_to_event_roles

Revision ID: 764d605cc18e
Revises: fd15240e2d65
Create Date: 2026-05-18 10:07:58.265743

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '764d605cc18e'
down_revision = 'fd15240e2d65'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('event_roles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('change_description', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('event_roles', schema=None) as batch_op:
        batch_op.drop_column('change_description')
