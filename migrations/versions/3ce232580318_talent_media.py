"""talent_media

Revision ID: 3ce232580318
Revises: 731556dfa9fb
Create Date: 2026-03-18 22:17:57.000288

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3ce232580318'
down_revision = '731556dfa9fb'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('talent_media',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('talent_id', sa.Integer(), nullable=False),
        sa.Column('media_type', sa.String(length=10), nullable=False),
        sa.Column('label', sa.String(length=200), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('talent_media')
