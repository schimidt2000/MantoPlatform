"""import_state_sync_fields

Revision ID: 4f391852ca6f
Revises: e2f3a4b5c6d7
Create Date: 2026-05-13 12:27:57.564341

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f391852ca6f'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('import_state', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_checked_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_import_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('import_state', schema=None) as batch_op:
        batch_op.drop_column('last_import_count')
        batch_op.drop_column('last_checked_at')
