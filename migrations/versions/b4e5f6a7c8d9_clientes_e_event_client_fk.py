"""clientes (CRM) + calendar_events.client_id (feature 094)

Revision ID: b4e5f6a7c8d9
Revises: a3d4e5f6a7b8
Create Date: 2026-06-29

- Cria a tabela ``clients`` (base de relacionamento/marketing importada do Kommo CSV ou criada
  manualmente). Identidade = telefone normalizado (``phone``, UNIQUE).
- Adiciona ``calendar_events.client_id`` (FK -> clients.id, nullable) para associar um cliente a cada
  evento; nullable garante grandfathering dos eventos passados.

Migration escrita a mao (autogenerate quebrado por drift pre-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "b4e5f6a7c8d9"
down_revision = "a3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("phone_display", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("company", sa.String(length=200), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("kommo_lead_id", sa.String(length=40), nullable=True),
        sa.Column("responsible", sa.String(length=120), nullable=True),
        sa.Column("tags", sa.String(length=300), nullable=True),
        sa.Column("lead_stage", sa.String(length=120), nullable=True),
        sa.Column("funnel", sa.String(length=120), nullable=True),
        sa.Column("lead_value", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("kommo_created_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone", name="uq_clients_phone"),
    )
    op.create_index("ix_clients_phone", "clients", ["phone"], unique=True)
    op.create_index("ix_clients_name", "clients", ["name"], unique=False)

    op.add_column(
        "calendar_events",
        sa.Column("client_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_calendar_events_client_id", "calendar_events", ["client_id"], unique=False
    )
    op.create_foreign_key(
        "fk_calendar_events_client_id", "calendar_events", "clients",
        ["client_id"], ["id"],
    )


def downgrade():
    op.drop_constraint("fk_calendar_events_client_id", "calendar_events", type_="foreignkey")
    op.drop_index("ix_calendar_events_client_id", table_name="calendar_events")
    op.drop_column("calendar_events", "client_id")

    op.drop_index("ix_clients_name", table_name="clients")
    op.drop_index("ix_clients_phone", table_name="clients")
    op.drop_table("clients")
