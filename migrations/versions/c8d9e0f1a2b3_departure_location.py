"""departure_location on calendar_events

Revision ID: c8d9e0f1a2b3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-30

Migration escrita à mão (autogenerate quebrado por drift pré-existente do schema).
Adiciona apenas a coluna departure_location em calendar_events.
"""
from alembic import op
import sqlalchemy as sa

revision = "c8d9e0f1a2b3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("calendar_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("departure_location", sa.String(length=300), nullable=True))


def downgrade():
    with op.batch_alter_table("calendar_events", schema=None) as batch_op:
        batch_op.drop_column("departure_location")
