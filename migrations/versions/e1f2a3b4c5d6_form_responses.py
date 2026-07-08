"""Respostas de formulários de pré-contrato + número WhatsApp destino (feature 118).

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-08
"""

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "form_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("form_type", sa.String(length=20), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("contact_name", sa.String(length=200), nullable=False),
        sa.Column("contact_phone", sa.String(length=20), nullable=True),
        sa.Column("contact_phone_display", sa.String(length=30), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", name="fk_form_responses_client_id"),
            nullable=True,
        ),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("calendar_events.id", name="fk_form_responses_event_id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_form_responses_contact_phone", "form_responses", ["contact_phone"])
    op.create_index("ix_form_responses_event_date", "form_responses", ["event_date"])
    op.create_index("ix_form_responses_client_id", "form_responses", ["client_id"])
    op.create_index("ix_form_responses_event_id", "form_responses", ["event_id"])
    op.add_column(
        "site_settings",
        sa.Column("whatsapp_form_number", sa.String(length=20), nullable=True),
    )


def downgrade():
    op.drop_column("site_settings", "whatsapp_form_number")
    op.drop_index("ix_form_responses_event_id", table_name="form_responses")
    op.drop_index("ix_form_responses_client_id", table_name="form_responses")
    op.drop_index("ix_form_responses_event_date", table_name="form_responses")
    op.drop_index("ix_form_responses_contact_phone", table_name="form_responses")
    op.drop_table("form_responses")
