"""vincular gasto extra a evento: special_expenses.event_id

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-06-01

Migration escrita à mão (autogenerate quebrado por drift pré-existente do schema).
"""
from alembic import op
import sqlalchemy as sa

revision = "e0f1a2b3c4d5"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("special_expenses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("event_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_special_expenses_event_id", ["event_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_special_expenses_event", "calendar_events", ["event_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("special_expenses", schema=None) as batch_op:
        batch_op.drop_constraint("fk_special_expenses_event", type_="foreignkey")
        batch_op.drop_index("ix_special_expenses_event_id")
        batch_op.drop_column("event_id")
