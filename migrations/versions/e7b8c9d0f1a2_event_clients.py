"""event_clients — múltiplos clientes por evento com tipo de relação (feature 100)

Revision ID: e7b8c9d0f1a2
Revises: d6a7b8c9e0f1
Create Date: 2026-07-01

Cria a tabela event_clients (associação evento↔cliente com relationship_type) e migra os vínculos
únicos existentes (calendar_events.client_id) como associação 'Contratante'. O campo client_id é mantido
(denormalizado, aponta para o contratante).

Migration escrita a mão (autogenerate quebrado por drift pré-existente).
"""
import sqlalchemy as sa
from alembic import op

revision = "e7b8c9d0f1a2"
down_revision = "d6a7b8c9e0f1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "event_clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(length=30), nullable=False,
                  server_default="Contratante"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["calendar_events.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_clients_event_id", "event_clients", ["event_id"], unique=False)
    op.create_index("ix_event_clients_client_id", "event_clients", ["client_id"], unique=False)

    # Data-migrate: cada vínculo único existente vira uma associação 'Contratante'.
    op.execute(
        "INSERT INTO event_clients (event_id, client_id, relationship_type, created_at) "
        "SELECT id, client_id, 'Contratante', CURRENT_TIMESTAMP "
        "FROM calendar_events WHERE client_id IS NOT NULL"
    )


def downgrade():
    op.drop_index("ix_event_clients_client_id", table_name="event_clients")
    op.drop_index("ix_event_clients_event_id", table_name="event_clients")
    op.drop_table("event_clients")
