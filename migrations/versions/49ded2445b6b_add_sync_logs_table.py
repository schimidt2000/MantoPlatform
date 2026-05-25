"""add sync_logs table

Revision ID: 49ded2445b6b
Revises: 1e617e199087
Create Date: 2026-05-25 12:08:27.502361

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '49ded2445b6b'
down_revision = '1e617e199087'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('sync_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('action', sa.String(length=30), nullable=False),
    sa.Column('event_title', sa.String(length=300), nullable=True),
    sa.Column('google_event_id', sa.String(length=200), nullable=True),
    sa.Column('event_id', sa.Integer(), nullable=True),
    sa.Column('details', sa.Text(), nullable=True),
    sa.Column('actor', sa.String(length=120), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sync_logs', schema=None) as batch_op:
        batch_op.create_index('ix_sync_logs_created_at', ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('sync_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_sync_logs_created_at')
    op.drop_table('sync_logs')
