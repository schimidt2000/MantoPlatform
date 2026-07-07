"""Confirmação de evento (feature 116).

calendar_events ganha confirmed_at/confirmed_by_id: registro simples de quem confirmou o
evento e quando, independente da mensagem de WhatsApp copiada pelo botão já existente.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a4
Create Date: 2026-07-07
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("calendar_events", sa.Column("confirmed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "calendar_events",
        sa.Column("confirmed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade():
    op.drop_column("calendar_events", "confirmed_by_id")
    op.drop_column("calendar_events", "confirmed_at")
