"""add_passport_status

Revision ID: 4868e4040dfe
Revises: 4f391852ca6f
Create Date: 2026-05-14 21:39:46.660405

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4868e4040dfe'
down_revision = '4f391852ca6f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('talents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('passport_status', sa.String(length=20), nullable=True))

    # Migra dados existentes: has_visa=True → 'visa', has_visa=False → 'none'
    op.execute("UPDATE talents SET passport_status = 'visa' WHERE has_visa = 1")
    op.execute("UPDATE talents SET passport_status = 'none' WHERE has_visa = 0")


def downgrade():
    with op.batch_alter_table('talents', schema=None) as batch_op:
        batch_op.drop_column('passport_status')
