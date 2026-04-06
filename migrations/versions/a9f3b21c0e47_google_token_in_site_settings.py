"""google_token_in_site_settings

Revision ID: a9f3b21c0e47
Revises: 2d9ac70022d0
Create Date: 2026-04-06 00:00:00.000000

Persiste o token OAuth do Google Calendar no banco para sobreviver a
redeploys em ambientes com filesystem efêmero (Railway, Heroku, etc.).
"""
from alembic import op
import sqlalchemy as sa


revision = 'a9f3b21c0e47'
down_revision = '2d9ac70022d0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_token', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('google_token')
