"""agrupamento de eventos por contrato: calendar_events.group_leader_id

Revision ID: q3f4a5b6c7d8
Revises: p2e3f4a5b6c7
Create Date: 2026-06-16

Adiciona:
- calendar_events.group_leader_id (Integer, FK self -> calendar_events.id):
  vincula um evento "satélite" ao evento "principal" do grupo comercial.
  Distinto de parent_event_id (vínculo de Ensaios) — mecanismo novo e
  independente, não reutiliza o campo existente.

Migration escrita à mão (autogenerate quebrado por drift pré-existente).
"""
from alembic import op
import sqlalchemy as sa

revision = "q3f4a5b6c7d8"
down_revision = "p2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("calendar_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_leader_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_calendar_events_group_leader", "calendar_events", ["group_leader_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("calendar_events", schema=None) as batch_op:
        batch_op.drop_constraint("fk_calendar_events_group_leader", type_="foreignkey")
        batch_op.drop_column("group_leader_id")
