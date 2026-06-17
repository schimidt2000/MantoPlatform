"""nome do agrupamento de eventos: calendar_events.group_name

Revision ID: r4a5b6c7d8e9
Revises: q3f4a5b6c7d8
Create Date: 2026-06-17

Adiciona:
- calendar_events.group_name (String(200), nullable): nome do grupo comercial,
  preenchido apenas no evento principal (feature 055). Usado como rótulo único do
  grupo na home comercial e nos balanços financeiros; quando NULL, exibe-se o título
  do evento como fallback.

Migration escrita à mão (autogenerate quebrado por drift pré-existente).
"""
from alembic import op
import sqlalchemy as sa

revision = "r4a5b6c7d8e9"
down_revision = "q3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("calendar_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_name", sa.String(length=200), nullable=True))


def downgrade():
    with op.batch_alter_table("calendar_events", schema=None) as batch_op:
        batch_op.drop_column("group_name")
