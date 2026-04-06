"""ensaio_materials

Revision ID: ea90a557b18e
Revises: 6cb2d9e5757f
Create Date: 2026-03-16 21:00:40.730850

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea90a557b18e'
down_revision = '6cb2d9e5757f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ensaio_materials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('material_type', sa.String(length=10), nullable=False),
        sa.Column('label', sa.String(length=200), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('ensaio_materials')
