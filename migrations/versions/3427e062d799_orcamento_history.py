"""orcamento_history

Revision ID: 3427e062d799
Revises: b3c4d5e6f7a8
Create Date: 2026-04-10 10:50:35.630863

"""
from alembic import op
import sqlalchemy as sa


revision = '3427e062d799'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'orcamento_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('client_name', sa.String(length=200), nullable=True),
        sa.Column('event_location', sa.String(length=300), nullable=True),
        sa.Column('event_date', sa.String(length=20), nullable=True),
        sa.Column('total_1h', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total_2h', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total_4h', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('has_show', sa.Boolean(), nullable=False),
        sa.Column('form_snapshot', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('orcamento_history', schema=None) as batch_op:
        batch_op.create_index('ix_orcamento_history_user_id', ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('orcamento_history', schema=None) as batch_op:
        batch_op.drop_index('ix_orcamento_history_user_id')
    op.drop_table('orcamento_history')
