"""educamanto packages and items

Revision ID: 5330027f6ccc
Revises: 6d694d44add2
Create Date: 2026-05-21 01:01:38.501354

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5330027f6ccc'
down_revision = '6d694d44add2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('educamanto_packages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('margin_1s', sa.Float(), nullable=False),
    sa.Column('margin_2s', sa.Float(), nullable=False),
    sa.Column('margin_1s_days', sa.Float(), nullable=False),
    sa.Column('margin_2s_days', sa.Float(), nullable=False),
    sa.Column('discount_days', sa.Integer(), nullable=False),
    sa.Column('discount_pct', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('educamanto_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('package_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('qty', sa.Integer(), nullable=False),
    sa.Column('cost_1s', sa.Float(), nullable=False),
    sa.Column('cost_2s', sa.Float(), nullable=False),
    sa.Column('cost_1s_days', sa.Float(), nullable=False),
    sa.Column('cost_2s_days', sa.Float(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['package_id'], ['educamanto_packages.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('educamanto_items')
    op.drop_table('educamanto_packages')
