"""event_role_travel_cache

Revision ID: 731556dfa9fb
Revises: 6fea6a5b4609
Create Date: 2026-03-18 22:14:54.546295

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '731556dfa9fb'
down_revision = '6fea6a5b4609'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('event_roles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('travel_cache', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('event_roles', schema=None) as batch_op:
        batch_op.drop_column('travel_cache')
