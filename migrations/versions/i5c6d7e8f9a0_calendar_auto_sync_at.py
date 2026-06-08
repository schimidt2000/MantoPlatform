"""calendar_auto_sync_at em site_settings (cron interno da agenda)

Revision ID: i5c6d7e8f9a0
Revises: h4b5c6d7e8f9
Create Date: 2026-06-08

Adiciona a coluna `calendar_auto_sync_at` (DateTime, nullable) em site_settings.
Usada como marcador da última sincronização automática da agenda e como "lock"
de execução única entre os workers (claim atômico via UPDATE condicional).

Migration escrita à mão (autogenerate quebrado por drift pré-existente).
"""
from alembic import op
import sqlalchemy as sa

revision = "i5c6d7e8f9a0"
down_revision = "h4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_settings") as batch_op:
        batch_op.add_column(sa.Column("calendar_auto_sync_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("site_settings") as batch_op:
        batch_op.drop_column("calendar_auto_sync_at")
