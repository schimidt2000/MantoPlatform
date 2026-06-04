"""orcamento congelado: orcamento_history.result_snapshot

Revision ID: f2a3b4c5d6e7
Revises: e0f1a2b3c4d5
Create Date: 2026-06-04

Migration escrita à mão (autogenerate quebrado por drift pré-existente do schema).
"""
from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7"
down_revision = "e0f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("orcamento_history", schema=None) as batch_op:
        batch_op.add_column(sa.Column("result_snapshot", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("orcamento_history", schema=None) as batch_op:
        batch_op.drop_column("result_snapshot")
