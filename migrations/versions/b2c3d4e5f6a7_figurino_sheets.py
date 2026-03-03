"""figurino_sheets table and figurino_sheet_id on event_roles

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'figurino_sheets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('character_name', sa.String(200), nullable=False),
        sa.Column('character_name_norm', sa.String(200), nullable=True),
        sa.Column('drive_file_id', sa.String(200), nullable=True),
        sa.Column('drive_url', sa.String(500), nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('drive_file_id'),
    )
    with op.batch_alter_table('event_roles') as batch_op:
        batch_op.add_column(sa.Column('figurino_sheet_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_event_role_figurino_sheet',
            'figurino_sheets',
            ['figurino_sheet_id'],
            ['id'],
        )


def downgrade():
    with op.batch_alter_table('event_roles') as batch_op:
        batch_op.drop_constraint('fk_event_role_figurino_sheet', type_='foreignkey')
        batch_op.drop_column('figurino_sheet_id')
    op.drop_table('figurino_sheets')
