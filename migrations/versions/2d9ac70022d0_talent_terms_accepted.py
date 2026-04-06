"""talent_terms_accepted

Revision ID: 2d9ac70022d0
Revises: f4ba2248a7ab
Create Date: 2026-03-26 11:49:39.788193

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d9ac70022d0'
down_revision = 'f4ba2248a7ab'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('talents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('terms_accepted_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('talents', schema=None) as batch_op:
        batch_op.drop_column('terms_accepted_at')
