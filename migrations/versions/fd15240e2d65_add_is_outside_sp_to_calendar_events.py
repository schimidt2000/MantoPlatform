"""add_is_outside_sp_to_calendar_events

Revision ID: fd15240e2d65
Revises: 4af0ad1b286b
Create Date: 2026-05-18 09:28:46.518057

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd15240e2d65'
down_revision = '4af0ad1b286b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_outside_sp', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.drop_column('is_outside_sp')
