"""release_date_setting

Revision ID: 6fea6a5b4609
Revises: ea90a557b18e
Create Date: 2026-03-17 15:46:08.147951

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6fea6a5b4609'
down_revision = 'ea90a557b18e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('release_date', sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('release_date')
