"""numeric sale transport acrescimo values

Revision ID: 6d694d44add2
Revises: 764d605cc18e
Create Date: 2026-05-19 19:38:41.010753

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d694d44add2'
down_revision = '764d605cc18e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.alter_column('sale_value',
               existing_type=sa.INTEGER(),
               type_=sa.Numeric(precision=12, scale=2),
               existing_nullable=True)
        batch_op.alter_column('transport_value',
               existing_type=sa.INTEGER(),
               type_=sa.Numeric(precision=12, scale=2),
               existing_nullable=True)
        batch_op.alter_column('acrescimo_value',
               existing_type=sa.INTEGER(),
               type_=sa.Numeric(precision=12, scale=2),
               existing_nullable=True)


def downgrade():
    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.alter_column('acrescimo_value',
               existing_type=sa.Numeric(precision=12, scale=2),
               type_=sa.INTEGER(),
               existing_nullable=True)
        batch_op.alter_column('transport_value',
               existing_type=sa.Numeric(precision=12, scale=2),
               type_=sa.INTEGER(),
               existing_nullable=True)
        batch_op.alter_column('sale_value',
               existing_type=sa.Numeric(precision=12, scale=2),
               type_=sa.INTEGER(),
               existing_nullable=True)
