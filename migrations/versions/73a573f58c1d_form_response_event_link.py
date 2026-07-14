"""Vínculo automático de formulário a evento: colunas de rastreio em form_responses (feature 126).

Revision ID: 73a573f58c1d
Revises: a51ce3dc4f3c
Create Date: 2026-07-13
"""

import sqlalchemy as sa
from alembic import op

revision = "73a573f58c1d"
down_revision = "a51ce3dc4f3c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "form_responses",
        sa.Column("event_link_source", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "form_responses",
        sa.Column(
            "event_link_ambiguous", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "form_responses",
        sa.Column(
            "event_link_locked", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade():
    op.drop_column("form_responses", "event_link_locked")
    op.drop_column("form_responses", "event_link_ambiguous")
    op.drop_column("form_responses", "event_link_source")
