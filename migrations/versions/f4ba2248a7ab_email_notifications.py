"""email_notifications

Revision ID: f4ba2248a7ab
Revises: d77f8e96ef34
Create Date: 2026-03-26 11:15:18.323807

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4ba2248a7ab'
down_revision = 'd77f8e96ef34'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_notifications_enabled', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('email_notifications_enabled')
