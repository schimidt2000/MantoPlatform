"""event_travel_distance_km

Revision ID: d77f8e96ef34
Revises: 3ce232580318
Create Date: 2026-03-18 23:08:52.082044

"""
from alembic import op
import sqlalchemy as sa


revision = 'd77f8e96ef34'
down_revision = '3ce232580318'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('travel_distance_km', sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.drop_column('travel_distance_km')
